"""
知乎数据获取模块

通过 DuckDuckGo 搜索 site:zhihu.com/question 获取知乎问题页面。
不直接爬取知乎，而是借助搜索引擎索引，合规风险极低。

知乎的问题页（/question/）是用户表达需求的地方：
  "有没有工具能…"、"推荐一下…"、"怎么解决…"
这类内容正是 SkillMatch 需要的需求信号。
"""

import time
from ddgs import DDGS

# 每次搜索返回的最大结果数
MAX_RESULTS_PER_QUERY = 8

# 两次请求之间的间隔（DDG 对频繁请求较敏感）
REQUEST_DELAY = 1.0

# 查询模板：围绕"需求表达"设计，不搜技术内容
# {skill} 会被替换为用户输入的技能
QUERY_TEMPLATES = [
    "site:zhihu.com/question 有没有 {skill} 工具",
    "site:zhihu.com/question {skill} 怎么解决 推荐",
    "site:zhihu.com/question {skill} 痛点 需求",
]

# 通用查询：不依赖技能，搜索独立开发者视角的需求帖
GENERIC_QUERIES = [
    "site:zhihu.com/question 独立开发者 找需求 产品方向",
    "site:zhihu.com/question 有没有好用的工具 自动化 效率",
    "site:zhihu.com/question 程序员 副业 技能变现 需求",
]


def fetch_zhihu_posts(skills: list[str]) -> list[dict]:
    """
    根据技能关键词搜索知乎问题，返回需求型帖子列表。

    Args:
        skills: 用户技能列表

    Returns:
        知乎问题帖子列表
    """
    posts = []
    seen_urls = set()

    queries = _build_queries(skills)

    with DDGS() as ddgs:
        for query in queries:
            try:
                results = list(ddgs.text(query, max_results=MAX_RESULTS_PER_QUERY))
                for r in results:
                    post = _normalize(r)
                    if post and post["url"] not in seen_urls:
                        # 只保留知乎 /question/ 页面
                        if "zhihu.com/question/" in post["url"]:
                            seen_urls.add(post["url"])
                            posts.append(post)
            except Exception:
                pass
            time.sleep(REQUEST_DELAY)

    return posts


def _build_queries(skills: list[str]) -> list[str]:
    """生成搜索查询列表：技能相关 + 通用需求查询"""
    queries = []

    # 技能相关查询（每个技能最多 1 个模板，控制请求数量）
    for skill in skills[:4]:  # 最多 4 个技能
        template = QUERY_TEMPLATES[0]  # 用最聚焦需求的模板
        queries.append(template.format(skill=skill))

    # 通用需求查询
    queries.extend(GENERIC_QUERIES[:2])

    return queries


def _normalize(result: dict) -> dict | None:
    """将 DDG 搜索结果统一为内部格式"""
    title = result.get("title", "").strip()
    url = result.get("href", "").strip()
    body = result.get("body", "").strip()

    # 过滤掉没有标题或 URL 的结果
    if not title or not url:
        return None

    # DDG 有时把 URL 当标题，过滤掉
    if title.startswith("zhihu.com/") or title.startswith("www.zhihu.com/"):
        if body:
            title = body[:50]  # 用摘要的前 50 字当标题
        else:
            return None

    return {
        "title": title,
        "content": body,
        "url": url,
        "source": "知乎",
        "replies": 0,  # DDG 结果没有回复数，设为 0
    }
