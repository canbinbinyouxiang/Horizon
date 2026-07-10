#!/usr/bin/env python3
"""
Telegram Channel Summarizer
抓取公开 Telegram 频道的新消息，用 DeepSeek 分析后推送飞书。
无需任何 Telegram API Key，直接解析 t.me/s 公开网页。
"""

import os
import re
import json
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from openai import OpenAI

# ── 配置 ──────────────────────────────────────────────────────────────────────
CHANNELS = [
    {"name": "A股研报快讯",   "id": "hgclhyyb"},
    {"name": "风向旗参考快讯", "id": "xhqcankao"},
]

FEISHU_WEBHOOK_URL  = os.environ["HORIZON_WEBHOOK_URL"]
DEEPSEEK_API_KEY    = os.environ["DEEPSEEK_API_KEY"]
SEEN_FILE           = "data/seen_tg_messages.json"
MAX_NEW_MESSAGES    = 60    # 每个频道最多处理 60 条新消息
MAX_CONTENT_CHARS   = 12000 # 送给 DeepSeek 的最大字符数
REQUEST_DELAY       = 2     # 两次请求之间的间隔（秒）
# ─────────────────────────────────────────────────────────────────────────────


# ── 状态持久化 ────────────────────────────────────────────────────────────────

def load_seen() -> dict:
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_seen(seen: dict):
    os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f, indent=2)


# ── 消息抓取 ──────────────────────────────────────────────────────────────────

def fetch_channel_messages(channel_id: str, last_seen_id: int) -> list[dict]:
    """
    抓取 t.me/s/{channel_id} 的最新消息，返回所有 ID > last_seen_id 的条目。
    每页约 20 条，如有更多新消息则向前翻页（最多翻 3 页）。
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }
    all_messages: list[dict] = []
    url = f"https://t.me/s/{channel_id}"

    for page in range(3):  # 最多翻 3 页
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            print(f"  ⚠️  第 {page+1} 页抓取失败: {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        page_messages: list[dict] = []
        oldest_id_on_page = None
        found_old = False

        for wrap in soup.select(".tgme_widget_message_wrap"):
            post_div = wrap.select_one(".tgme_widget_message")
            if not post_div:
                continue

            # 解析消息 ID（data-post="channelname/12345"）
            data_post = post_div.get("data-post", "")
            m = re.search(r"/(\d+)$", data_post)
            if not m:
                continue
            msg_id = int(m.group(1))

            if oldest_id_on_page is None or msg_id < oldest_id_on_page:
                oldest_id_on_page = msg_id

            if msg_id <= last_seen_id:
                found_old = True
                continue

            # 提取消息文本
            text_div = wrap.select_one(".tgme_widget_message_text")
            text = text_div.get_text(separator="\n", strip=True) if text_div else ""
            if not text:
                continue

            # 提取时间
            time_el = wrap.select_one("time")
            msg_time = time_el.get("datetime", "")[:16] if time_el else ""

            page_messages.append({"id": msg_id, "text": text, "time": msg_time})

        all_messages.extend(page_messages)

        # 如果本页已经包含旧消息，或者找不到更早的页，停止翻页
        if found_old or not oldest_id_on_page or oldest_id_on_page <= last_seen_id:
            break

        # 翻到上一页（older 参数）
        url = f"https://t.me/s/{channel_id}?before={oldest_id_on_page}"
        time.sleep(REQUEST_DELAY)

    # 去重、按 ID 升序排列，截取最新的 N 条
    seen_ids: set[int] = set()
    unique: list[dict] = []
    for msg in all_messages:
        if msg["id"] not in seen_ids:
            seen_ids.add(msg["id"])
            unique.append(msg)
    unique.sort(key=lambda x: x["id"])
    return unique[-MAX_NEW_MESSAGES:]


# ── DeepSeek 分析 ─────────────────────────────────────────────────────────────

def summarize_channel(channel_name: str, messages: list[dict]) -> str:
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    content_lines = []
    for m in messages:
        t = m["time"] or "—"
        content_lines.append(f"[{t}] {m['text']}")
    content = "\n\n".join(content_lines)

    prompt = f"""你是一名专业的金融与科技分析师。以下是 Telegram 频道「{channel_name}」的最新推送消息，请进行整合分析：

{content[:MAX_CONTENT_CHARS]}

请按以下结构输出（使用 Markdown）：

## 重要资讯摘要
（列出 5-8 条最值得关注的信息，每条一行，保留关键数字和机构名称）

## 市场影响分析
（从宏观经济、行业动态、政策变化等角度综合分析，150 字以内）

## 板块与个股影响

强度说明——利好：🔥🔥🔥 强 | 🔥🔥 中 | 🔥 弱；利空：❄️❄️❄️ 强 | ❄️❄️ 中 | ❄️ 弱
（强=直接政策/数据驱动，短期有明确催化剂；中=间接影响，中期逻辑；弱=边际影响，逻辑链较长）

**利好板块/题材**
逐条列出，每条格式为：
- 🔥🔥🔥/🔥🔥/🔥 **板块/题材名称**：利好逻辑（1-2 句）→ 龙头个股：股票名称（代码）、股票名称（代码）……

**利空板块/题材**
逐条列出，每条格式为：
- ❄️❄️❄️/❄️❄️/❄️ **板块/题材名称**：利空逻辑（1-2 句）→ 龙头个股：股票名称（代码）、股票名称（代码）……

（若无明显影响，注明"暂无明显利空/利好"）
"""

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.3,
    )
    return resp.choices[0].message.content


# ── 飞书推送 ──────────────────────────────────────────────────────────────────

def send_to_feishu(channel_name: str, summary: str, msg_count: int) -> bool:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    message = {
        "msg_type": "interactive",
        "card": {
            "schema": "2.0",
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📡 {channel_name} 动态汇总",
                },
                "template": "green",
            },
            "body": {
                "elements": [
                    {
                        "tag": "markdown",
                        "content": f"📅 {now}  |  📨 {msg_count} 条新消息",
                    },
                    {"tag": "hr"},
                    {"tag": "markdown", "content": summary},
                ]
            },
        },
    }
    resp = requests.post(FEISHU_WEBHOOK_URL, json=message, timeout=10)
    return resp.status_code == 200


# ── 主流程 ────────────────────────────────────────────────────────────────────

def process_channel(channel: dict, seen: dict):
    channel_id   = channel["id"]
    channel_name = channel["name"]
    last_seen_id = seen.get(channel_id, 0)

    print(f"\n{'='*50}")
    print(f"📡 频道：{channel_name} (@{channel_id})")
    print(f"  上次已读消息 ID: {last_seen_id}")

    messages = fetch_channel_messages(channel_id, last_seen_id)
    if not messages:
        print("  ✅ 没有新消息，跳过。")
        return

    print(f"  🆕 发现 {len(messages)} 条新消息，开始分析...")
    summary = summarize_channel(channel_name, messages)
    success = send_to_feishu(channel_name, summary, len(messages))
    print(f"  {'✅ 已推送飞书' if success else '❌ 飞书推送失败'}")

    # 记录最新消息 ID
    seen[channel_id] = messages[-1]["id"]


def main():
    seen = load_seen()

    for channel in CHANNELS:
        try:
            process_channel(channel, seen)
        except Exception as e:
            print(f"  ❌ 频道 {channel['name']} 处理失败: {e}")
        time.sleep(REQUEST_DELAY)

    save_seen(seen)
    print("\n✅ 所有频道处理完成。")


if __name__ == "__main__":
    main()
