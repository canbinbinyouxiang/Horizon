#!/usr/bin/env python3
"""
YouTube Transcriber
获取 YouTube 频道新视频的字幕或 MiMo ASR 转写内容，原文分段推送飞书，不做 AI 分析。
"""

import os
import re
import json
import glob
import math
import base64
import subprocess
import tempfile
import requests
import feedparser
from html.parser import HTMLParser
from openai import OpenAI
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)

# ── 配置 ──────────────────────────────────────────────────────────────────────
CHANNELS = [
    {"name": "oldpowerful",      "id": "UC8gZZWIWmBuCb_gzC8DUrvw"},
    {"name": "laomanpindao2049", "id": "UCrAC23izk57G7jCBPfdXGkg"},
]

FEISHU_WEBHOOK_URL = os.environ["HORIZON_WEBHOOK_URL"]
SEEN_FILE          = "data/seen_transcribed.json"  # 独立于 summarizer 的记录
MAX_RECENT_VIDEOS  = 5
CHUNK_SIZE         = 3000   # 每条飞书消息最多 3000 字
CHUNK_MAX_BYTES    = 6 * 1024 * 1024  # MiMo ASR 单段上限
# ─────────────────────────────────────────────────────────────────────────────


# ── 工具函数 ──────────────────────────────────────────────────────────────────

class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)
    def get_text(self):
        return " ".join(self.parts)

def strip_html(html: str) -> str:
    s = _HTMLStripper()
    s.feed(html)
    return s.get_text()


# ── 频道 & 视频信息 ────────────────────────────────────────────────────────────

def get_latest_videos(channel_id: str) -> list[dict]:
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    feed = feedparser.parse(rss_url)
    videos = []
    for entry in feed.entries[:MAX_RECENT_VIDEOS]:
        videos.append({
            "id":          entry.yt_videoid,
            "title":       entry.title,
            "url":         entry.link,
            "published":   entry.published,
            "description": strip_html(entry.get("summary", "")),
        })
    return videos


# ── 字幕获取 ──────────────────────────────────────────────────────────────────

def get_transcript(video_id: str) -> str | None:
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
    except AttributeError:
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        except Exception:
            return None
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception:
        return None

    for lang_codes in [["zh-Hans", "zh", "zh-TW", "zh-Hant"], ["en"]]:
        try:
            t = transcript_list.find_transcript(lang_codes)
            data = t.fetch()
            return " ".join(item.get("text", "") for item in data)
        except Exception:
            pass
    try:
        t = transcript_list.find_generated_transcript(["zh-Hans", "zh", "zh-TW", "en"])
        data = t.fetch()
        return " ".join(item.get("text", "") for item in data)
    except Exception:
        pass
    return None


# ── MiMo ASR 音频转写 ─────────────────────────────────────────────────────────

def download_audio(video_id: str) -> str | None:
    raw_path = f"/tmp/{video_id}_raw.%(ext)s"
    raw_mp3  = f"/tmp/{video_id}_raw.mp3"
    out_path = f"/tmp/{video_id}.mp3"
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    cmd = [
        "yt-dlp", "-x",
        "--audio-format", "mp3",
        "--audio-quality", "5",
        "--no-playlist",
        "--no-check-certificates",
        "-o", raw_path,
        video_url,
    ]
    cookies_file = "/tmp/youtube_cookies.txt"
    if os.path.exists(cookies_file):
        cmd.extend(["--cookies", cookies_file])
        print("  🍪 使用 cookies 下载")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            print(f"  ⚠️  yt-dlp 失败（exit {result.returncode}）: {result.stderr[-200:]}")
            return None
        if not os.path.exists(raw_mp3):
            print("  ⚠️  音频文件未找到")
            return None
    except Exception as e:
        print(f"  ⚠️  yt-dlp 异常: {e}")
        return None

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", raw_mp3, "-b:a", "32k", "-ar", "16000", out_path],
            capture_output=True, timeout=120, check=True,
        )
        os.unlink(raw_mp3)
        return out_path
    except Exception as e:
        print(f"  ⚠️  ffmpeg 重编码失败，使用原始文件: {e}")
        os.rename(raw_mp3, out_path)
        return out_path


def split_audio(audio_path: str) -> list[str]:
    file_size = os.path.getsize(audio_path)
    if file_size <= CHUNK_MAX_BYTES:
        return [audio_path]

    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", audio_path],
        capture_output=True, text=True, timeout=30,
    )
    duration = float(json.loads(probe.stdout)["format"]["duration"])
    num_chunks = math.ceil(file_size / CHUNK_MAX_BYTES)
    seg_time = int(duration / num_chunks)
    base = audio_path.replace(".mp3", "")
    subprocess.run(
        ["ffmpeg", "-y", "-i", audio_path,
         "-f", "segment", "-segment_time", str(seg_time), "-c", "copy", f"{base}_%03d.mp3"],
        capture_output=True, timeout=120,
    )
    chunks = sorted(glob.glob(f"{base}_*.mp3"))
    return chunks if chunks else [audio_path]


def transcribe_chunk(audio_path: str, mimo_key: str) -> str:
    with open(audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("utf-8")
    client = OpenAI(api_key=mimo_key, base_url="https://api.xiaomimimo.com/v1")
    resp = client.chat.completions.create(
        model="mimo-v2.5-asr",
        messages=[{"role": "user", "content": [{
            "type": "input_audio",
            "input_audio": {"data": f"data:audio/mpeg;base64,{audio_b64}"},
        }]}],
        extra_body={"asr_options": {"language": "zh"}},
    )
    return resp.choices[0].message.content or ""


def get_transcript_via_mimo_asr(video_id: str) -> str | None:
    mimo_key = os.environ.get("MIMO_API_KEY")
    if not mimo_key:
        print("  ⚠️  未配置 MIMO_API_KEY，跳过 ASR")
        return None

    print("  🎵 下载音频...")
    audio_path = download_audio(video_id)
    if not audio_path:
        return None

    print(f"  ✅ 下载完成（{os.path.getsize(audio_path) // 1024} KB）")
    chunks = split_audio(audio_path)
    print(f"  📦 共 {len(chunks)} 段，开始逐段转写...")

    texts = []
    for i, chunk in enumerate(chunks, 1):
        print(f"  🔤 转写第 {i}/{len(chunks)} 段...")
        try:
            text = transcribe_chunk(chunk, mimo_key)
            if text:
                texts.append(text)
        except Exception as e:
            print(f"  ⚠️  第 {i} 段失败: {e}")
        finally:
            if chunk != audio_path and os.path.exists(chunk):
                os.unlink(chunk)

    if os.path.exists(audio_path):
        os.unlink(audio_path)

    result = " ".join(texts).strip()
    return result or None


# ── 飞书推送（分段）─────────────────────────────────────────────────────────────

def send_to_feishu(video: dict, text: str, source_label: str):
    """将转写文本分段推送到飞书，每段 CHUNK_SIZE 字"""
    chunks = [text[i:i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
    total = len(chunks)
    success_count = 0

    for idx, chunk in enumerate(chunks, 1):
        part_label = f"第 {idx}/{total} 段" if total > 1 else "完整"
        message = {
            "msg_type": "interactive",
            "card": {
                "schema": "2.0",
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"📝 {video['title']}",
                    },
                    "template": "purple",
                },
                "body": {
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": (
                                f"🔗 [点击观看]({video['url']})  |  "
                                f"📅 {video['published']}  |  "
                                f"📌 {source_label}  |  {part_label}"
                            ),
                        },
                        {"tag": "hr"},
                        {"tag": "markdown", "content": chunk},
                    ]
                },
            },
        }
        resp = requests.post(FEISHU_WEBHOOK_URL, json=message, timeout=10)
        if resp.status_code == 200:
            success_count += 1
        else:
            print(f"  ⚠️  第 {idx} 段推送失败（HTTP {resp.status_code}）")

    print(f"  {'✅' if success_count == total else '⚠️'} 推送 {success_count}/{total} 段")


# ── 状态管理 ──────────────────────────────────────────────────────────────────

def load_seen() -> set:
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE) as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()


def save_seen(seen: set):
    os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
    with open(SEEN_FILE, "w") as f:
        json.dump(sorted(seen), f, indent=2)


# ── 主流程 ────────────────────────────────────────────────────────────────────

def process_channel(channel: dict, seen: set):
    print(f"\n{'='*50}")
    print(f"📡 频道：{channel['name']}  ({channel['id']})")
    videos = get_latest_videos(channel["id"])
    new_videos = [v for v in videos if v["id"] not in seen]

    if not new_videos:
        print("  ✅ 没有新视频，跳过。")
        return

    print(f"  🆕 发现 {len(new_videos)} 条新视频，开始转写...")

    for video in new_videos:
        print(f"\n▶ {video['title']}")
        transcript = None
        source_label = ""

        # 1. 尝试 YouTube 字幕
        transcript = get_transcript(video["id"])
        if transcript:
            source_label = "YouTube 字幕"
            print(f"  ✅ 获取到字幕（{len(transcript)} 字符）")
        else:
            # 2. MiMo ASR
            print("  🔍 无字幕，尝试 MiMo ASR...")
            transcript = get_transcript_via_mimo_asr(video["id"])
            if transcript:
                source_label = "MiMo ASR"
                print(f"  ✅ ASR 转写成功（{len(transcript)} 字符）")
            else:
                print("  ⚠️  无法获取转写内容，跳过。")
                seen.add(video["id"])
                continue

        send_to_feishu(video, transcript, source_label)
        seen.add(video["id"])


def main():
    seen = load_seen()

    for channel in CHANNELS:
        try:
            process_channel(channel, seen)
        except Exception as e:
            print(f"  ❌ 频道 {channel['name']} 处理失败: {e}")

    save_seen(seen)
    print("\n✅ 所有频道处理完成。")


if __name__ == "__main__":
    main()
