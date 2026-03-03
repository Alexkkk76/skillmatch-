"""
语义匹配引擎

将用户技能与社区帖子做语义相似度计算，返回最相关的内容。

匹配逻辑分三步：
  1. 过滤掉"内容型"帖子（周刊、教程、摘要等），留下讨论/需求型帖子
  2. 语义相似度：技能描述 vs 帖子内容
  3. 需求信号加分：含"有没有""looking for""wish existed"等词的帖子得分更高

使用 sentence-transformers 多语言模型（支持中英文混合），
约 120MB，首次运行自动下载，之后复用本地缓存。
"""

import re
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# ── 过滤规则：内容型帖子（技术文章、周刊、教程）────────────────────────
# 命中这些模式的帖子大概率是"内容"而非"需求"，直接排除
_CONTENT_PATTERNS = [
    # 中文：周刊 / 月刊 / 摘要 / 年度盘点
    r"周刊[#＃\s]*\d+",          # "Python 周刊#60"
    r"月刊[#＃\s]*\d+",
    r"（摘要）",
    r"\(摘要\)",
    r"年度(盘点|总结|回顾)",
    r"^\[?教程\]?",
    r"入门(教程|指南|介绍)",
    r"完全指南",
    # 英文：newsletter / weekly / roundup / tutorial
    r"\bweekly\b",
    r"\bnewsletter\b",
    r"\broundup\b",
    r"\btutorial\b",
    r"\bintroduction to\b",
    r"\bgetting started with\b",
    r"\bcheat sheet\b",
]
_CONTENT_RE = re.compile("|".join(_CONTENT_PATTERNS), re.IGNORECASE)

# ── 需求信号：帖子里有这些词，说明用户在表达需求 ────────────────────────
_NEED_SIGNALS_ZH = [
    "有没有", "有没有工具", "求推荐", "推荐一下", "求个",
    "哪个工具", "有什么好的", "能不能", "想找", "找不到",
    "有人知道", "有没有人做过", "需要一个", "做一个",
    "希望有", "要是有就好了", "痛点", "不方便", "麻烦",
]
_NEED_SIGNALS_EN = [
    "is there a", "looking for", "wish existed", "does anyone know",
    "what tool", "recommend", "i need", "can't find", "cannot find",
    "anyone built", "would love", "pain point", "frustrating",
    "no good tool", "wish there was",
]
_NEED_SIGNAL_BOOST = 0.12   # 命中需求信号的加分幅度


class SkillMatcher:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)

    def match(
        self, skills: list[str], posts: list[dict], top_k: int = 10
    ) -> list[dict]:
        """
        返回与技能最匹配的 top_k 条需求型帖子。

        Args:
            skills:  用户技能列表，如 ['Python', '爬虫', '数据可视化']
            posts:   抓取到的帖子列表
            top_k:   返回结果数量

        Returns:
            按综合得分降序排列的帖子列表，每项附加 score 字段（0~1）
        """
        # 步骤 1：过滤内容型帖子 & 标题过短的帖子
        valid_posts = [
            p for p in posts
            if len(p.get("title", "")) >= 6 and not _is_content_post(p)
        ]
        if not valid_posts:
            return []

        # 步骤 2：语义匹配
        # 查询文本强调"需求/痛点"场景，而非技术本身
        query = (
            "用户需要解决的问题和痛点，需要用到 "
            + "、".join(skills)
            + " 相关技能才能实现的工具或产品"
        )
        post_texts = [
            p["title"] + " " + p.get("content", "")[:200]
            for p in valid_posts
        ]

        query_vec = self.model.encode([query])
        post_vecs = self.model.encode(
            post_texts, batch_size=64, show_progress_bar=False
        )
        semantic_scores = _cosine_sim(query_vec, post_vecs)[0]

        # 步骤 3：需求信号加分，结果 clamp 到 [0, 1]
        final_scores = np.array([
            min(1.0, float(semantic_scores[i]) + _need_signal_score(valid_posts[i]))
            for i in range(len(valid_posts))
        ])

        # 取 top_k
        top_indices = np.argsort(final_scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            post = valid_posts[idx].copy()
            post["score"] = float(final_scores[idx])
            results.append(post)

        return results


# ── 辅助函数 ──────────────────────────────────────────────────────────


def _is_content_post(post: dict) -> bool:
    """判断是否为技术内容帖（周刊、教程、摘要等），是则返回 True 表示过滤掉"""
    text = post.get("title", "") + " " + post.get("content", "")
    return bool(_CONTENT_RE.search(text))


def _need_signal_score(post: dict) -> float:
    """
    检测帖子是否含有需求信号词，返回加分值（0 或 BOOST）。
    中文信号和英文信号各计一次，最多加两次。
    """
    text = (post.get("title", "") + " " + post.get("content", "")).lower()
    boost = 0.0
    if any(s in text for s in _NEED_SIGNALS_ZH):
        boost += _NEED_SIGNAL_BOOST
    if any(s in text for s in _NEED_SIGNALS_EN):
        boost += _NEED_SIGNAL_BOOST
    return boost


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a / np.linalg.norm(a, axis=1, keepdims=True)
    b = b / np.linalg.norm(b, axis=1, keepdims=True)
    return np.dot(a, b.T)
