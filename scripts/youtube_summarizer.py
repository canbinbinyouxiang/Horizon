#!/usr/bin/env python3
"""
YouTube Video Summarizer
监听 YouTube 频道新视频，提取字幕，用 DeepSeek 总结后推送飞书。
"""

import os
import re
import json
import requests
import feedparser
from openai import OpenAI
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)

# ── 配置 ──────────────────────────────────────────────────────────────────────
CHANNEL_HANDLE = "@oldpowerful"
FEISHU_WEBHOOK_URL = os.environ["HORIZON_WEBHOOK_URL"]
DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
SEEN_VIDEOS_FILE = "data/seen_videos.json"
MAX_TRANSCRIPT_CHARS = 8000   # 截断过长字幕，节省 token
MAX_RECENT_VIDEOS = 5         # 每次最多处理最新 5 条
# ─────────────────────────────────────────────────────────────────────────────


def get_channel_id(handle: str) -> str:
    """从 YouTube 频道页面提取 channel_id"""
    url = f"https://www.youtube.com/{handle}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    resp.raise_for_status()
    match = re.search(r'"channelId":"(UC[^"]{20,})"', resp.text)
    if match:
        return match.group(1)
    # 备用匹配
    match = re.search(r'channel/([^"/?]+)', resp.text)
    if match:
        return match.group(1)
    raise ValueError(
        f"无法获取 {handle} 的 channel_id，请手动填写 CHANNEL_ID 环境变量"
    )


def get_latest_videos(channel_id: str) -> list[dict]:
    """通过 YouTube RSS 获取最新视频列表"""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    feed = feedparser.parse(rss_url)
    videos = []
    for entry in feed.entries[:MAX_RECENT_VIDEOS]:
        videos.append(
            {
                "id": entry.yt_videoid,
                "title": entry.title,
                "url": entry.link,
                "published": entry.published,
            }
        )
    return videos


def get_transcript(video_id: str) -> str | None:
    """获取视频字幕，优先中文，其次英文"""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        # 优先顺序：简体中文 → 繁体中文 → 自动生成中文 → 英文
        for lang_codes in [
            ["zh-Hans", "zh", "zh-TW", "zh-Hant"],
            ["en"],
        ]:
            try:
                t = transcript_list.find_transcript(lang_codes)
                data = t.fetch()
                return " ".join(item["text"] for item in data)
            except Exception:
                pass
        # 最后尝试自动生成的中文
        t = transcript_list.find_generated_transcript(["zh-Hans", "zh", "zh-TW"])
        data = t.fetch()
        return " ".join(item["text"] for item in data)
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception as e:
        print(f"  ⚠️  获取字幕失败: {e}")
        return None


def summarize(title: str, transcript: str) -> str:
    """用 DeepSeek 总结视频内容"""
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
    )
    prompt = f"""你是一名专业的内容分析师。请对以下 YouTube 视频进行深度总结：

【视频标题】
{title}

【字幕原文】
{transcript[:MAX_TRANSCRIPT_CHARS]}

请按以下结构输出（使用 Markdown）：

## 核心观点
（列出 3-5 个最重要的观点，每条一行）

## 内容摘要
（150-200 字，简洁概括视频主旨）

## 值得关注
（博主提到的有价值的信息、数据或建议）
"""
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.3,
    )
    return resp.choices[0].message.content


def send_to_feishu(video: dict, summary: str) -> bool:
    """推送飞书消息"""
    message = {
        "msg_type": "interactive",
        "card": {
            "schema": "2.0",
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📺 新视频：{video['title']}",
                },
                "template": "blue",
            },
            "body": {
                "elements": [
                    {
                        "tag": "markdown",
                        "content": f"🔗 [点击观看视频]({video['url']})\n📅 发布时间：{video['published']}",
                    },
                    {"tag": "hr"},
                    {"tag": "markdown", "content": summary},
                ]
            },
        },
    }
    resp = requests.post(FEISHU_WEBHOOK_URL, json=message, timeout=10)
    return resp.status_code == 200


def load_seen_videos() -> set:
    if os.path.exists(SEEN_VIDEOS_FILE):
        with open(SEEN_VIDEOS_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen_videos(seen: set):
    os.makedirs(os.path.dirname(SEEN_VIDEOS_FILE), exist_ok=True)
    with open(SEEN_VIDEOS_FILE, "w") as f:
        json.dump(sorted(seen), f, indent=2)


def main():
    print(f"🔍 正在获取频道 {CHANNEL_HANDLE} 的信息...")

    # 支持通过环境变量直接指定 channel_id，跳过自动获取
    channel_id = os.environ.get("YOUTUBE_CHANNEL_ID") or get_channel_id(CHANNEL_HANDLE)
    print(f"✅ Channel ID: {channel_id}")

    videos = get_latest_videos(channel_id)
    print(f"📋 获取到 {len(videos)} 条视频")

    seen = load_seen_videos()
    new_videos = [v for v in videos if v["id"] not in seen]

    if not new_videos:
        print("✅ 没有新视频，跳过。")
        return

    print(f"🆕 发现 {len(new_videos)} 条新视频，开始处理...")

    for video in new_videos:
        print(f"\n▶ {video['title']}")
        transcript = get_transcript(video["id"])

        if not transcript:
            print("  ⚠️  该视频无可用字幕，跳过总结。")
            # 即使没字幕也标记为已处理，避免重复尝试
            seen.add(video["id"])
            continue

        print(f"  📝 字幕长度: {len(transcript)} 字符，开始总结...")
        summary = summarize(video["title"], transcript)

        success = send_to_feishu(video, summary)
        if success:
            print("  ✅ 已推送飞书")
        else:
            print("  ❌ 飞书推送失败")

        seen.add(video["id"])

    save_seen_videos(seen)
    print("\n✅ 全部处理完成。")


if __name__ == "__main__":
    main()
