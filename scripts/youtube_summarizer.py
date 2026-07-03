#!/usr/bin/env python3
"""
YouTube Video Summarizer
监听 YouTube 频道新视频，提取字幕或研报 PDF，用 DeepSeek 总结后推送飞书。
"""

import os
import re
import json
import glob
import math
import base64
import zipfile
import subprocess
import tempfile
import requests
import feedparser
import pdfplumber
from html.parser import HTMLParser
from openai import OpenAI
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)

# ── 配置 ──────────────────────────────────────────────────────────────────────
# 监听的频道列表，新增频道在此追加即可
CHANNELS = [
    {"name": "oldpowerful",    "id": "UC8gZZWIWmBuCb_gzC8DUrvw"},
    {"name": "laomanpindao2049", "id": "UCrAC23izk57G7jCBPfdXGkg"},
]

FEISHU_WEBHOOK_URL = os.environ["HORIZON_WEBHOOK_URL"]
DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
SEEN_VIDEOS_FILE = "data/seen_videos.json"
MAX_TRANSCRIPT_CHARS = 8000
MAX_RECENT_VIDEOS = 5
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
    """通过 YouTube RSS 获取最新视频，包含描述"""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    feed = feedparser.parse(rss_url)
    videos = []
    for entry in feed.entries[:MAX_RECENT_VIDEOS]:
        videos.append({
            "id": entry.yt_videoid,
            "title": entry.title,
            "url": entry.link,
            "published": entry.published,
            "description": strip_html(entry.get("summary", "")),
        })
    return videos


def get_full_description(video_id: str, rss_desc: str) -> str:
    """
    RSS 描述可能被截断，若未找到 Drive 链接则用 yt-dlp 获取完整描述。
    """
    if "drive.google.com" in rss_desc or "docs.google.com" in rss_desc:
        return rss_desc
    try:
        result = subprocess.run(
            ["yt-dlp", "--skip-download", "--print", "description",
             f"https://www.youtube.com/watch?v={video_id}"],
            capture_output=True, text=True, timeout=30,
        )
        desc = result.stdout.strip()
        return desc if desc else rss_desc
    except Exception:
        return rss_desc


# ── 字幕获取 ──────────────────────────────────────────────────────────────────

def get_transcript(video_id: str) -> str | None:
    """尝试获取 YouTube 字幕（新旧版 API 兼容）"""
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

CHUNK_MAX_BYTES = 6 * 1024 * 1024   # 6MB 原始音频 ≈ Base64 后约 8MB，留安全余量


def download_audio(video_id: str) -> str | None:
    """
    用 yt-dlp 下载音频，再用 ffmpeg 重编码为低码率 MP3。
    分两步可避免 yt-dlp postprocessor 参数格式问题。
    """
    raw_path = f"/tmp/{video_id}_raw.%(ext)s"
    raw_mp3 = f"/tmp/{video_id}_raw.mp3"
    out_path = f"/tmp/{video_id}.mp3"
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    # 基础下载命令
    cmd = [
        "yt-dlp", "-x",
        "--audio-format", "mp3",
        "--audio-quality", "5",        # VBR ~128kbps，转码前用默认质量
        "--no-playlist",
        "--no-check-certificates",
        "-o", raw_path,
        video_url,
    ]

    # 如果存在 cookies 文件则使用（绕过 bot 检测）
    cookies_file = "/tmp/youtube_cookies.txt"
    if os.path.exists(cookies_file):
        cmd.extend(["--cookies", cookies_file])
        print("  🍪 使用 cookies 下载")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            print(f"  ⚠️  yt-dlp 失败（exit {result.returncode}）")
            print(f"      stderr: {result.stderr[-300:]}")
            return None
        if not os.path.exists(raw_mp3):
            print("  ⚠️  音频文件未找到")
            return None
    except Exception as e:
        print(f"  ⚠️  yt-dlp 异常: {e}")
        return None

    # 用 ffmpeg 重编码为低码率（减小体积，方便分段）
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", raw_mp3,
             "-b:a", "32k", "-ar", "16000", out_path],
            capture_output=True, timeout=120, check=True,
        )
        os.unlink(raw_mp3)
        return out_path
    except Exception as e:
        print(f"  ⚠️  ffmpeg 重编码失败，使用原始文件: {e}")
        # 重编码失败时直接用原始 mp3
        os.rename(raw_mp3, out_path)
        return out_path


def split_audio(audio_path: str) -> list[str]:
    """若音频超过 CHUNK_MAX_BYTES，用 ffmpeg 按时长等分切片"""
    file_size = os.path.getsize(audio_path)
    if file_size <= CHUNK_MAX_BYTES:
        return [audio_path]

    # 获取总时长
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", audio_path],
        capture_output=True, text=True, timeout=30,
    )
    duration = float(json.loads(probe.stdout)["format"]["duration"])

    num_chunks = math.ceil(file_size / CHUNK_MAX_BYTES)
    seg_time = int(duration / num_chunks)

    base = audio_path.replace(".mp3", "")
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", audio_path,
            "-f", "segment",
            "-segment_time", str(seg_time),
            "-c", "copy",
            f"{base}_%03d.mp3",
        ],
        capture_output=True, timeout=120,
    )
    chunks = sorted(glob.glob(f"{base}_*.mp3"))
    return chunks if chunks else [audio_path]


def transcribe_chunk(audio_path: str, mimo_key: str) -> str:
    """将单段音频 Base64 编码后发给 MiMo ASR，返回文字"""
    with open(audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("utf-8")

    client = OpenAI(api_key=mimo_key, base_url="https://api.xiaomimimo.com/v1")
    resp = client.chat.completions.create(
        model="mimo-v2.5-asr",
        messages=[{
            "role": "user",
            "content": [{
                "type": "input_audio",
                "input_audio": {"data": f"data:audio/mpeg;base64,{audio_b64}"},
            }],
        }],
        extra_body={"asr_options": {"language": "zh"}},
    )
    return resp.choices[0].message.content or ""


def get_transcript_via_mimo_asr(video_id: str) -> str | None:
    """完整 ASR 流程：下载 → 分段 → 逐段转写 → 拼接"""
    mimo_key = os.environ.get("MIMO_API_KEY")
    if not mimo_key:
        print("  ⚠️  未配置 MIMO_API_KEY，跳过 ASR")
        return None

    print("  🎵 下载音频...")
    audio_path = download_audio(video_id)
    if not audio_path:
        return None

    file_size = os.path.getsize(audio_path)
    print(f"  ✅ 音频下载完成（{file_size // 1024} KB）")

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
            print(f"  ⚠️  第 {i} 段转写失败: {e}")
        finally:
            if chunk != audio_path and os.path.exists(chunk):
                os.unlink(chunk)

    if os.path.exists(audio_path):
        os.unlink(audio_path)

    result = " ".join(texts).strip()
    return result or None


# ── Google Drive 研报下载 ──────────────────────────────────────────────────────

def extract_gdrive_file_id(text: str) -> str | None:
    """从描述文本中提取 Google Drive 文件 ID"""
    patterns = [
        r'drive\.google\.com/file/d/([A-Za-z0-9_-]+)',
        r'drive\.google\.com/open\?id=([A-Za-z0-9_-]+)',
        r'docs\.google\.com/\w+/d/([A-Za-z0-9_-]+)',
        r'drive\.google\.com/uc\?.*id=([A-Za-z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def download_gdrive_pdf(file_id: str) -> bytes | None:
    """下载 Google Drive 文件，处理大文件确认页面"""
    session = requests.Session()
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    resp = session.get(url, timeout=30)

    # Google Drive 对大文件会返回确认页面
    if "confirm=" in resp.text or "virus scan warning" in resp.text.lower():
        confirm_match = re.search(r'confirm=([A-Za-z0-9_-]+)', resp.text)
        if confirm_match:
            confirm_token = confirm_match.group(1)
            url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm={confirm_token}"
            resp = session.get(url, timeout=60)

    if resp.status_code == 200 and len(resp.content) > 1000:
        return resp.content
    return None


def extract_pdf_text(pdf_bytes: bytes) -> str | None:
    """从 PDF 字节提取纯文本"""
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            tmp_path = f.name
        text_parts = []
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        os.unlink(tmp_path)
        return "\n".join(text_parts) or None
    except Exception as e:
        print(f"  ⚠️  PDF 解析失败: {e}")
        return None


def extract_zip_text(zip_bytes: bytes) -> str | None:
    """解压 ZIP，提取其中所有 PDF 的文本并合并"""
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = os.path.join(tmp_dir, "report.zip")
            with open(zip_path, "wb") as f:
                f.write(zip_bytes)
            with zipfile.ZipFile(zip_path, "r") as zf:
                pdf_names = [n for n in zf.namelist() if n.lower().endswith(".pdf")]
                if not pdf_names:
                    print("  ⚠️  ZIP 内未找到 PDF 文件")
                    return None
                print(f"  📦 ZIP 内含 {len(pdf_names)} 个 PDF：{', '.join(pdf_names)}")
                all_texts = []
                for name in pdf_names:
                    pdf_bytes_inner = zf.read(name)
                    text = extract_pdf_text(pdf_bytes_inner)
                    if text:
                        all_texts.append(f"=== {name} ===\n{text}")
                return "\n\n".join(all_texts) or None
    except Exception as e:
        print(f"  ⚠️  ZIP 解压失败: {e}")
        return None


def parse_file_bytes(file_bytes: bytes) -> str | None:
    """根据文件魔数自动识别 PDF / ZIP 并提取文本"""
    if file_bytes[:4] == b'%PDF':
        print("  📄 检测为 PDF 格式")
        return extract_pdf_text(file_bytes)
    elif file_bytes[:2] == b'PK':
        print("  📦 检测为 ZIP 格式，正在解压...")
        return extract_zip_text(file_bytes)
    else:
        print("  ⚠️  未知文件格式，跳过解析")
        return None


def get_report_text(description: str) -> str | None:
    """完整流程：从描述提取链接 → 下载 → 自动识别格式 → 解析文本"""
    file_id = extract_gdrive_file_id(description)
    if not file_id:
        return None
    print(f"  📎 找到 Drive 文件 ID: {file_id}，正在下载...")
    pdf_bytes = download_gdrive_pdf(file_id)
    if not pdf_bytes:
        print("  ⚠️  文件下载失败")
        return None
    print(f"  ✅ 下载完成（{len(pdf_bytes)//1024} KB），自动识别格式...")
    return parse_file_bytes(pdf_bytes)


# ── DeepSeek 总结 ─────────────────────────────────────────────────────────────

def summarize(title: str, content: str, content_type: str = "transcript") -> str:
    """用 DeepSeek 总结，根据内容类型调整 prompt"""
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    if content_type == "report":
        source_desc = "以下是该视频附带的研报原文"
    elif content_type == "transcript":
        source_desc = "以下是该视频的字幕原文"
    else:  # title_only
        source_desc = "（无字幕和研报，请结合你的金融知识对标题中的信息进行展开解读）\n以下仅有视频标题"

    prompt = f"""你是一名专业的金融分析师。请对以下内容进行深度解读：

【视频标题】
{title}

【内容来源】{source_desc}：
{content[:MAX_TRANSCRIPT_CHARS]}

请按以下结构输出（使用 Markdown）：

## 核心观点
（列出 3-5 个最重要的结论，每条一行）

## 内容摘要
（150-200 字，简洁概括主旨）

## 数据与细节
（提炼报告中的关键数字、机构观点、时间节点）

## 值得关注
（对投资者或研究者最有价值的信息或风险提示）
"""
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.3,
    )
    return resp.choices[0].message.content


# ── 飞书推送 ──────────────────────────────────────────────────────────────────

def send_to_feishu(video: dict, summary: str, source_label: str) -> bool:
    message = {
        "msg_type": "interactive",
        "card": {
            "schema": "2.0",
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"📺 {video['title']}"},
                "template": "blue",
            },
            "body": {
                "elements": [
                    {
                        "tag": "markdown",
                        "content": (
                            f"🔗 [点击观看视频]({video['url']})\n"
                            f"📅 {video['published']}  |  📌 来源：{source_label}"
                        ),
                    },
                    {"tag": "hr"},
                    {"tag": "markdown", "content": summary},
                ]
            },
        },
    }
    resp = requests.post(FEISHU_WEBHOOK_URL, json=message, timeout=10)
    return resp.status_code == 200


# ── 状态管理 ──────────────────────────────────────────────────────────────────

def load_seen_videos() -> set:
    if os.path.exists(SEEN_VIDEOS_FILE):
        with open(SEEN_VIDEOS_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen_videos(seen: set):
    os.makedirs(os.path.dirname(SEEN_VIDEOS_FILE), exist_ok=True)
    with open(SEEN_VIDEOS_FILE, "w") as f:
        json.dump(sorted(seen), f, indent=2)


# ── 主流程 ────────────────────────────────────────────────────────────────────

def process_channel(channel: dict, seen: set):
    """处理单个频道的新视频"""
    print(f"\n{'='*50}")
    print(f"📡 频道：{channel['name']}  ({channel['id']})")
    videos = get_latest_videos(channel["id"])
    print(f"📋 获取到 {len(videos)} 条视频")

    new_videos = [v for v in videos if v["id"] not in seen]
    if not new_videos:
        print("✅ 没有新视频，跳过。")
        return

    print(f"🆕 发现 {len(new_videos)} 条新视频，开始处理...")

    for video in new_videos:
        print(f"\n▶ {video['title']}")
        content = None
        content_type = "title_only"
        source_label = "标题分析"

        # 1. 尝试字幕
        transcript = get_transcript(video["id"])
        if transcript:
            content = transcript
            content_type = "transcript"
            source_label = "字幕"
            print(f"  ✅ 获取到字幕（{len(transcript)} 字符）")
        else:
            # 2. 尝试 MiMo ASR 音频转写
            print("  🔍 无字幕，尝试 MiMo ASR 音频转写...")
            asr_text = get_transcript_via_mimo_asr(video["id"])
            if asr_text:
                content = asr_text
                content_type = "transcript"
                source_label = "MiMo ASR"
                print(f"  ✅ ASR 转写成功（{len(asr_text)} 字符）")
            else:
                # 3. 尝试研报 PDF
                print("  🔍 ASR 失败，尝试从描述获取研报...")
                desc = get_full_description(video["id"], video["description"])
                report_text = get_report_text(desc)
                if report_text:
                    content = report_text
                    content_type = "report"
                    source_label = "研报 PDF"
                    print(f"  ✅ 研报解析成功（{len(report_text)} 字符）")
                else:
                    # 4. 兜底：标题分析
                    print("  📝 使用标题进行分析...")
                    content = video["title"]
                    content_type = "title_only"
                    source_label = "标题分析"

        summary = summarize(video["title"], content, content_type)
        success = send_to_feishu(video, summary, source_label)
        print(f"  {'✅ 已推送飞书' if success else '❌ 飞书推送失败'}")
        seen.add(video["id"])


def main():
    seen = load_seen_videos()

    for channel in CHANNELS:
        try:
            process_channel(channel, seen)
        except Exception as e:
            print(f"  ❌ 频道 {channel['name']} 处理失败: {e}")

    save_seen_videos(seen)
    print("\n✅ 所有频道处理完成。")


if __name__ == "__main__":
    main()
