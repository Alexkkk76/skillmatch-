"""
Reddit 数据获取模块

使用 Reddit 公开 JSON 接口（无需 API Key），
抓取独立开发、创业、SaaS 相关 subreddit 的热门帖子。
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta

import requests

CACHE_FILE = Path(__file__).parent.parent / "cache" / "reddit.json"
CACHE_TTL_HOURS = 2

HEADERS = {
    # Reddit 要求 User-Agent 包含联系信息
    "User-Agent": "SkillMatch/1.0 (skill-need matching tool; contact: github.com/skillmatch)",
}

# 与独立开发、创业、技能变现相关的 subreddit
TARGET_SUBREDDITS = [
    "sideprojects",     # 副业项目
    "indiehackers",     # 独立开发者
    "SaaS",             # SaaS 产品
    "startups",         # 创业
    "entrepreneur",     # 创业者
    "nocode",           # 无代码工具
    "webdev",           # Web 开发
    "freelance",        # 自由职业
    "learnprogramming", # 学编程的人（= 有需求的潜在用户）
]


def fetch_reddit_posts() -> list[dict]:
    """获取 Reddit 相关帖子，优先读缓存"""
    cached = _load_cache()
    if cached is not None:
        return cached

    posts = []
    for subreddit in TARGET_SUBREDDITS:
        batch = _fetch_subreddit(subreddit)
        posts.extend(batch)
        time.sleep(0.5)  # Reddit 对频繁请求较敏感，适当延迟

    # 按 URL 去重
    seen, unique = set(), []
    for p in posts:
        if p["url"] not in seen:
            seen.add(p["url"])
            unique.append(p)

    _save_cache(unique)
    return unique


def _fetch_subreddit(subreddit: str) -> list[dict]:
    """抓取某个 subreddit 近一周的热门帖子"""
    try:
        resp = requests.get(
            f"https://www.reddit.com/r/{subreddit}/top.json",
            params={"t": "week", "limit": 25},
            headers=HEADERS,
            timeout=12,
        )
        resp.raise_for_status()
        children = resp.json().get("data", {}).get("children", [])
        return [_normalize(c["data"]) for c in children if c.get("data")]
    except Exception:
        return []


def _normalize(post: dict) -> dict:
    return {
        "title": post.get("title", "").strip(),
        "content": post.get("selftext", "").strip()[:300],
        "url": f"https://www.reddit.com{post.get('permalink', '')}",
        "source": f"Reddit/r/{post.get('subreddit', '')}",
        "replies": post.get("num_comments", 0),
        "score": post.get("score", 0),  # Reddit 赞数（不与匹配 score 混用）
    }


def _load_cache() -> list | None:
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        cached_at = datetime.fromisoformat(data["cached_at"])
        if datetime.now() - cached_at < timedelta(hours=CACHE_TTL_HOURS):
            return data["posts"]
    except Exception:
        pass
    return None


def _save_cache(posts: list):
    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(
            {"cached_at": datetime.now().isoformat(), "posts": posts},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
