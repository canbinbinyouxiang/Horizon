#!/usr/bin/env python3
"""
Stock Daily Analyst v2
先从东方财富、搜索 API、Telegram 抓取最新资讯，再喂给 DeepSeek 分析，推送飞书。
"""

import os
import json
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from openai import OpenAI

# ── 股票列表 ──────────────────────────────────────────────────────────────────
STOCKS = [
    {
        "name":    "小米集团",
        "code":    "01810.HK",
        "market":  "港股",
        "aliases": ["小米", "01810"],      # Telegram 关键词
    },
    {
        "name":    "三安光电",
        "code":    "600703.SH",
        "market":  "A股",
        "aliases": ["三安", "600703"],
    },
    {
        "name":    "腾讯音乐",
        "code":    "01698.HK",
        "market":  "港股",
        "aliases": ["TME", "腾讯音乐"],
    },
    {
        "name":    "中国核电",
        "code":    "601985.SH",
        "market":  "A股",
        "aliases": ["601985", "中国核电"],
    },
    {
        "name":    "中国核建",
        "code":    "601611.SH",
        "market":  "A股",
        "aliases": ["601611", "中国核建"],
    },
    {
        "name":    "紫金矿业",
        "code":    "601899.SH",
        "market":  "A股",
        "aliases": ["601899", "紫金矿业"],
    },
    {
        "name":    "宏桥控股",
        "code":    "002379.SZ",
        "market":  "A股",
        "aliases": ["002379", "宏桥控股"],
    },
    {
        "name":    "中科曙光",
        "code":    "603019.SH",
        "market":  "A股",
        "aliases": ["603019", "中科曙光"],
    },
    {
        "name":    "中国中免",
        "code":    "01880.HK",
        "market":  "港股",
        "aliases": ["01880", "中国中免"],
    },
    {
        "name":    "晶泰控股",
        "code":    "02228.HK",
        "market":  "港股",
        "aliases": ["02228", "晶泰控股"],
    },
]

# ── Telegram 研报频道 ─────────────────────────────────────────────────────────
TELEGRAM_CHANNELS = ["hgclhyyb", "xhqcankao","hgclhyyb","ReutersZh","qzdzb","hejzl_xjk","Guanshuitan"]

# ── 环境变量 ──────────────────────────────────────────────────────────────────
STOCK_WEBHOOK_URL = os.environ["STOCK_WEBHOOK_URL"]
DEEPSEEK_API_KEY  = os.environ["DEEPSEEK_API_KEY"]
SERPER_API_KEY    = os.environ.get("SERPER_API_KEY", "")   # 可选，优先使用

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://www.eastmoney.com/",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


# ══════════════════════════════════════════════════════════════════════════════
# 1. 东方财富新闻
# ══════════════════════════════════════════════════════════════════════════════

def fetch_eastmoney_news(stock: dict) -> list[str]:
    """抓取东方财富搜索页的股票相关新闻标题"""
    results = []
    name = stock["name"]

    # ① 搜索页（HTML）
    try:
        url = (
            "https://search.eastmoney.com/web/result"
            f"?keyword={requests.utils.quote(name)}&type=news&pageindex=1&pagesize=20"
        )
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        # 尝试常见选择器
        items = (
            soup.select(".news-item")
            or soup.select(".search-news-item")
            or soup.select("li.newsList-item")
            or soup.select(".articleList .item")
            or soup.select("a.title")
        )

        seen = set()
        for item in items[:15]:
            if item.name == "a":
                title = item.get_text(strip=True)
            else:
                a = item.select_one("a.title") or item.select_one("h3 a") or item.select_one("a")
                title = a.get_text(strip=True) if a else ""

            if title and len(title) > 5 and title not in seen:
                results.append(title)
                seen.add(title)
            if len(results) >= 10:
                break

    except Exception as e:
        print(f"    ⚠️  东方财富搜索失败: {e}")

    # ② 降级：抓东方财富全市场快讯，按关键词过滤
    if not results:
        try:
            url2 = (
                "https://np-cms.eastmoney.com/api/Info/GetList"
                "?type=10&pageindex=1&pagesize=50&callback=&client=&fields=Title,ShowTime"
            )
            resp2 = requests.get(url2, headers=HEADERS, timeout=10)
            data  = resp2.json().get("Data", {}).get("List", [])
            keywords = [name] + stock.get("aliases", [])
            for item in data:
                title = item.get("Title", "")
                if any(kw in title for kw in keywords):
                    results.append(title)
        except Exception as e:
            print(f"    ⚠️  东方财富快讯降级失败: {e}")

    print(f"    东方财富：{len(results)} 条")
    return results[:10]


# ══════════════════════════════════════════════════════════════════════════════
# 2. 搜索 API（Serper → DuckDuckGo 降级）
# ══════════════════════════════════════════════════════════════════════════════

def fetch_search_news(stock: dict) -> list[str]:
    """搜索引擎查询股票近一周资讯（优先 Serper，降级 DuckDuckGo）"""
    query   = f"{stock['name']} {stock['code']} 最新消息"
    results = []

    # ① Serper
    if SERPER_API_KEY:
        try:
            resp = requests.post(
                "https://google.serper.dev/news",
                headers={
                    "X-API-KEY": SERPER_API_KEY,
                    "Content-Type": "application/json",
                },
                json={"q": query, "gl": "cn", "hl": "zh-cn", "num": 10},
                timeout=10,
            )
            for item in resp.json().get("news", [])[:10]:
                title   = item.get("title", "")
                snippet = item.get("snippet", "")[:100]
                results.append(f"{title}：{snippet}" if snippet else title)
            print(f"    Serper：{len(results)} 条")
            return results
        except Exception as e:
            print(f"    ⚠️  Serper 失败: {e}，降级 DuckDuckGo")

    # ② DuckDuckGo（免费，无需 Key）
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            hits = list(ddgs.news(query, max_results=10, region="cn-zh", timelimit="w"))
        for r in hits:
            title = r.get("title", "")
            body  = r.get("body", "")[:100]
            results.append(f"{title}：{body}" if body else title)
        print(f"    DuckDuckGo：{len(results)} 条")
    except Exception as e:
        print(f"    ⚠️  DuckDuckGo 失败: {e}")

    return results[:10]


# ══════════════════════════════════════════════════════════════════════════════
# 3. Telegram 研报频道
# ══════════════════════════════════════════════════════════════════════════════

def fetch_telegram_news(stock: dict) -> list[str]:
    """从公开 Telegram 研报频道抓取与该股相关的消息"""
    keywords = [stock["name"]] + stock.get("aliases", [])
    matched  = []

    for channel_id in TELEGRAM_CHANNELS:
        try:
            url  = f"https://t.me/s/{channel_id}"
            resp = requests.get(
                url,
                headers={"User-Agent": HEADERS["User-Agent"]},
                timeout=15,
            )
            soup  = BeautifulSoup(resp.text, "html.parser")
            wraps = soup.select(".tgme_widget_message_wrap")
            for wrap in wraps:
                text_el = wrap.select_one(".tgme_widget_message_text")
                if not text_el:
                    continue
                text = text_el.get_text(separator=" ", strip=True)
                if any(kw in text for kw in keywords):
                    matched.append(text[:400])
        except Exception as e:
            print(f"    ⚠️  Telegram {channel_id} 失败: {e}")

    print(f"    Telegram：{len(matched)} 条")
    return matched[:8]


# ══════════════════════════════════════════════════════════════════════════════
# DeepSeek 分析
# ══════════════════════════════════════════════════════════════════════════════

def analyze_stock(stock: dict) -> tuple[dict, dict]:
    """
    抓取三路新闻，汇总后交给 DeepSeek 分析。
    返回 (analysis_dict, news_stats_dict)
    """
    print(f"  📰 抓取新闻资讯...")
    em_news     = fetch_eastmoney_news(stock)
    search_news = fetch_search_news(stock)
    tg_news     = fetch_telegram_news(stock)

    news_stats = {
        "eastmoney": len(em_news),
        "search":    len(search_news),
        "telegram":  len(tg_news),
    }

    sections = []
    if em_news:
        sections.append("【东方财富新闻】\n" + "\n".join(f"· {n}" for n in em_news[:8]))
    if search_news:
        sections.append("【搜索引擎最新资讯】\n" + "\n".join(f"· {n}" for n in search_news[:8]))
    if tg_news:
        sections.append("【Telegram 研报频道】\n" + "\n".join(f"· {m}" for m in tg_news[:5]))

    news_context = (
        "\n\n".join(sections)
        if sections
        else "（暂未获取到实时新闻，请基于训练数据进行分析）"
    )

    today  = datetime.now().strftime("%Y-%m-%d")
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    prompt = f"""你是一名专业的股票研究员。以下是关于 {stock['name']}（{stock['code']}，{stock['market']}）截至今天（{today}）的最新资讯：

{news_context}

请基于以上实时资讯进行分析，严格按以下 JSON 格式输出，不要输出任何其他内容：

{{
  "positive": ["利好1（引用具体资讯）", "利好2"],
  "negative": ["利空1（引用具体资讯）", "利空2"],
  "short_term": {{
    "direction": "上涨/下跌/震荡",
    "reason": "1-2句核心理由，引用资讯依据"
  }},
  "long_term": {{
    "direction": "上涨/下跌/震荡",
    "reason": "1-2句核心理由"
  }},
  "rating": "买入/增持/持有/减持/卖出",
  "summary": "不超过60字的整体评价"
}}

要求：
- 优先基于提供的实时资讯，训练数据作为背景补充
- positive/negative 若无明显消息返回 []
- direction 只能是"上涨"、"下跌"、"震荡"之一
- rating 只能是"买入"、"增持"、"持有"、"减持"、"卖出"之一"""

    resp = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content), news_stats


# ══════════════════════════════════════════════════════════════════════════════
# 飞书推送
# ══════════════════════════════════════════════════════════════════════════════

DIRECTION_ICON = {"上涨": "📈", "下跌": "📉", "震荡": "↔️"}
RATING_COLOR   = {
    "买入": ("🟢", "green"),
    "增持": ("🟢", "green"),
    "持有": ("🟡", "yellow"),
    "减持": ("🔴", "red"),
    "卖出": ("🔴", "red"),
}


def send_stock_card(stock: dict, analysis: dict, news_stats: dict):
    positive   = analysis.get("positive", [])
    negative   = analysis.get("negative", [])
    short_term = analysis.get("short_term", {})
    long_term  = analysis.get("long_term", {})
    rating     = analysis.get("rating", "持有")
    summary    = analysis.get("summary", "")

    emoji, color = RATING_COLOR.get(rating, ("🟡", "yellow"))

    def dir_label(d: str) -> str:
        return f"{DIRECTION_ICON.get(d, '')} {d}"

    lines = []

    lines.append("**🔥 利好消息**")
    if positive:
        lines.extend(f"- {item}" for item in positive)
    else:
        lines.append("- 暂无明显利好")

    lines.append("")
    lines.append("**❄️ 利空消息**")
    if negative:
        lines.extend(f"- {item}" for item in negative)
    else:
        lines.append("- 暂无明显利空")

    lines.append("")
    lines.append(
        f"**近期预期（1-4周）**：{dir_label(short_term.get('direction', '—'))}\n"
        f"{short_term.get('reason', '')}"
    )
    lines.append("")
    lines.append(
        f"**远期预期（3-12月）**：{dir_label(long_term.get('direction', '—'))}\n"
        f"{long_term.get('reason', '')}"
    )
    if summary:
        lines.append("")
        lines.append(f"> {summary}")

    # 数据来源注脚
    src_parts = []
    if news_stats.get("eastmoney"):
        src_parts.append(f"东方财富 {news_stats['eastmoney']} 条")
    if news_stats.get("search"):
        src_parts.append(f"搜索 {news_stats['search']} 条")
    if news_stats.get("telegram"):
        src_parts.append(f"Telegram {news_stats['telegram']} 条")
    source_note = "📡 " + " | ".join(src_parts) if src_parts else "📡 训练数据"

    message = {
        "msg_type": "interactive",
        "card": {
            "schema": "2.0",
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"{emoji} {stock['name']}（{stock['code']}）— {rating}",
                },
                "template": color,
            },
            "body": {
                "elements": [
                    {
                        "tag": "markdown",
                        "content": (
                            f"📅 {datetime.now().strftime('%Y-%m-%d')}  |  "
                            f"{stock['market']}  |  {source_note}"
                        ),
                    },
                    {"tag": "hr"},
                    {"tag": "markdown", "content": "\n".join(lines)},
                ]
            },
        },
    }

    resp = requests.post(STOCK_WEBHOOK_URL, json=message, timeout=10)
    ok   = resp.status_code == 200
    print(f"  {'✅' if ok else '❌'} 飞书推送{'成功' if ok else f'失败（{resp.status_code}）'}")


# ══════════════════════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print(f"📊 股票日报 — {datetime.now().strftime('%Y-%m-%d')}\n")
    for stock in STOCKS:
        print(f"{'=' * 50}")
        print(f"🔍 分析 {stock['name']}（{stock['code']}）...")
        try:
            analysis, news_stats = analyze_stock(stock)
            send_stock_card(stock, analysis, news_stats)
        except Exception as e:
            print(f"  ❌ 失败: {e}")
        time.sleep(2)   # 避免请求过快
    print("\n✅ 所有股票分析完成。")


if __name__ == "__main__":
    main()
