"""
Hacker News 数据获取模块

使用 HN 官方 Algolia 搜索 API（无需认证），
重点抓取 "Ask HN" 类帖子（用户提问 = 真实需求），
以及 "Show HN" 类帖子（开发者展示 = 市场验证信号）。
"""

import requests

HEADERS = {
    "User-Agent": "SkillMatch/1.0",
}

# HN Algolia API 文档：https://hn.algolia.com/api
HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


def fetch_hn_posts(skills: list[str]) -> list[dict]:
    """
    搜索与技能相关的 HN 帖子。

    优先搜索：
    1. "Ask HN" 类帖子（用户表达需求、求推荐）
    2. 技能关键词相关的 Story
    """
    posts = []
    seen_ids = set()

    # 1. 通用需求类帖子：Ask HN 里的工具需求
    ask_queries = [
        "Ask HN: what software do you wish existed",
        "Ask HN: is there a tool",
        "Ask HN: looking for",
        "Ask HN: recommend",
    ]
    for query in ask_queries:
        for post in _search(query, tags="ask_hn", hits=10):
            if post["id"] not in seen_ids:
                seen_ids.add(post["id"])
                posts.append(post)

    # 2. 技能关键词相关的 Story（包含 Show HN、普通讨论）
    for skill in skills[:5]:  # 最多 5 个技能，避免请求过多
        for post in _search(skill, tags="story", hits=15):
            if post["id"] not in seen_ids:
                seen_ids.add(post["id"])
                posts.append(post)

    return posts


def _search(query: str, tags: str = "story", hits: int = 20) -> list[dict]:
    try:
        resp = requests.get(
            HN_SEARCH_URL,
            params={
                "query": query,
                "tags": tags,
                "hitsPerPage": hits,
                # 只取近半年的帖子
                "numericFilters": "created_at_i>1735689600",  # 2025-01-01
            },
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        hits_data = resp.json().get("hits", [])
        return [_normalize(h) for h in hits_data]
    except Exception:
        return []


def _normalize(hit: dict) -> dict:
    story_id = hit.get("objectID", "")
    return {
        "id": story_id,
        "title": hit.get("title", "").strip(),
        "content": hit.get("story_text", "").strip()[:300] if hit.get("story_text") else "",
        "url": hit.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
        "source": "HN",
        "replies": hit.get("num_comments", 0),
    }
