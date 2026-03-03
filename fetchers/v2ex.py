"""
V2EX 数据获取模块

使用 V2EX 公开 API（无需认证）抓取热门话题和独立开发相关节点的内容。
数据会缓存到本地 cache/ 目录，2 小时内重复运行不重复请求。
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta

import requests

CACHE_FILE = Path(__file__).parent.parent / "cache" / "v2ex.json"
CACHE_TTL_HOURS = 2

HEADERS = {
    "User-Agent": "SkillMatch/1.0 (https://github.com/your-name/skillmatch)",
}

# 抓取的节点：独立开发、创业、编程、职业相关
TARGET_NODES = [
    "indie",        # 独立开发
    "startup",      # 创业
    "programmer",   # 程序员
    "python",       # Python
    "career",       # 职业发展
    "create",       # 创造
    "share",        # 分享发现
    "design",       # 设计
]


def fetch_v2ex_posts() -> list[dict]:
    """获取 V2EX 相关话题，优先从本地缓存读取"""
    cached = _load_cache()
    if cached is not None:
        return cached

    posts = []

    # 1. 热门话题（最多 40 条）
    posts.extend(_fetch_hot())

    # 2. 各节点最新话题
    for node in TARGET_NODES:
        posts.extend(_fetch_node(node))
        time.sleep(0.3)  # 礼貌性延迟

    # 按 URL 去重
    seen, unique = set(), []
    for p in posts:
        if p["url"] not in seen:
            seen.add(p["url"])
            unique.append(p)

    _save_cache(unique)
    return unique


def _fetch_hot() -> list[dict]:
    try:
        resp = requests.get(
            "https://www.v2ex.com/api/topics/hot.json",
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        return [_normalize(t) for t in resp.json()]
    except Exception:
        return []


def _fetch_node(node_name: str) -> list[dict]:
    try:
        resp = requests.get(
            f"https://www.v2ex.com/api/topics/show.json?node_name={node_name}",
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            return []
        return [_normalize(t) for t in data]
    except Exception:
        return []


def _normalize(topic: dict) -> dict:
    """统一字段格式"""
    return {
        "title": topic.get("title", "").strip(),
        "content": topic.get("content", "").strip(),
        "url": f"https://www.v2ex.com/t/{topic.get('id', '')}",
        "source": "V2EX",
        "replies": topic.get("replies", 0),
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
