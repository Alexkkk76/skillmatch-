"""
少数派数据获取模块

使用少数派公开搜索 API 根据技能关键词抓取相关文章。
无需认证，直接请求即可。
"""

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Referer": "https://sspai.com",
}

# 除了用户技能外，额外补充的搜索词（覆盖独立开发常见痛点场景）
EXTRA_KEYWORDS = ["效率工具", "独立开发", "自动化", "工具推荐"]


def fetch_sspai_posts(skills: list[str]) -> list[dict]:
    """
    根据技能关键词搜索少数派文章。

    每个关键词搜索 15 条，合并去重后返回。
    """
    posts = []
    seen_ids = set()

    keywords = skills + EXTRA_KEYWORDS
    for kw in keywords[:8]:  # 最多 8 个关键词，避免请求过慢
        for article in _search(kw):
            if article["id"] not in seen_ids:
                seen_ids.add(article["id"])
                posts.append(article)

    return posts


def _search(keyword: str) -> list[dict]:
    try:
        resp = requests.get(
            "https://sspai.com/api/v1/article/tag/page/get",
            params={"limit": 15, "tag": keyword, "offset": 0},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        articles = data.get("data", [])
        if not isinstance(articles, list):
            return []
        return [_normalize(a) for a in articles]
    except Exception:
        return []


def _normalize(article: dict) -> dict:
    article_id = article.get("id", "")
    return {
        "id": article_id,
        "title": article.get("title", "").strip(),
        "content": article.get("summary", "").strip(),
        "url": f"https://sspai.com/post/{article_id}",
        "source": "少数派",
        "replies": article.get("comment_count", 0),
    }
