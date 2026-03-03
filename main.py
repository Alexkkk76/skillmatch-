#!/usr/bin/env python3
"""
SkillMatch - 技能 × 需求自动匹配工具

输入你的技能，自动扫描开发者社区的真实讨论，
找到「我能做、有人要」的产品方向。

用法示例：
  python main.py                                   # 交互模式
  python main.py -s "Python,爬虫,数据可视化"
  python main.py -s "UI设计,Figma,交互设计" --top 5
  python main.py -s "Python,机器学习" --export results.md
  python main.py -s "Python" --sources v2ex        # 只搜 V2EX
"""

import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from fetchers.v2ex import fetch_v2ex_posts
from fetchers.sspai import fetch_sspai_posts
from fetchers.reddit import fetch_reddit_posts
from fetchers.hn import fetch_hn_posts
from fetchers.zhihu import fetch_zhihu_posts
from matcher import SkillMatcher

console = Console()

ALL_SOURCES = "v2ex,sspai,reddit,hn,zhihu"

# 技能示例，按类别分组展示
SKILL_EXAMPLES = {
    "💻 开发": ["Python", "JavaScript", "Go", "爬虫", "数据分析", "机器学习", "iOS开发", "Android开发"],
    "🎨 设计": ["UI设计", "Figma", "插画", "平面设计", "3D建模", "动效设计"],
    "🎬 内容": ["视频剪辑", "After Effects", "写作", "摄影", "播客"],
    "📊 其他": ["Excel", "数据可视化", "英语翻译", "SEO", "运营", "自动化"],
}

# 数据源列表，供交互模式逐条展示
SOURCE_OPTIONS = [
    ("v2ex",   "V2EX  ", "中文独立开发者社区"),
    ("sspai",  "少数派 ", "效率工具与数字生活"),
    ("reddit", "Reddit", "英文独立开发者社区"),
    ("hn",     "HN    ", "Hacker News"),
    ("zhihu",  "知乎  ", "中文问答社区"),
]


def _interactive_prompt() -> tuple[list[str], int, str, str | None]:
    """交互模式：引导用户逐步输入参数，返回 (skills, top, sources, export)"""
    console.print()
    console.rule("[bold cyan]⚡ SkillMatch 技能需求匹配[/bold cyan]")
    console.print(
        "\n[bold]欢迎使用 SkillMatch！[/bold]\n"
        "我会帮你从社区讨论中找到与你技能匹配的产品方向。\n"
    )

    # ── 1. 技能输入（附示例） ─────────────────────────────────────
    console.print("🎯 [bold]你有哪些技能？[/bold]\n")
    for category, examples in SKILL_EXAMPLES.items():
        console.print(f"   {category}：[dim]{' · '.join(examples)}[/dim]")

    console.print()
    while True:
        raw = Prompt.ask("   输入你的技能（逗号分隔，例如：Python,爬虫）")
        skills = [s.strip() for s in raw.split(",") if s.strip()]
        if skills:
            break
        console.print("[red]   请至少输入一个技能[/red]")

    # ── 2. 返回数量 ───────────────────────────────────────────────
    while True:
        raw_n = Prompt.ask("\n📊 [bold]返回结果数量[/bold]（1-10）", default="10")
        try:
            top = int(raw_n)
            if 1 <= top <= 10:
                break
            console.print("[red]   请输入 1 到 10 之间的数字[/red]")
        except ValueError:
            console.print("[red]   请输入一个数字[/red]")

    # ── 3. 数据源（逐条勾选） ─────────────────────────────────────
    console.print("\n📡 [bold]选择搜索的数据源[/bold]（直接回车 = 全选）\n")
    for i, (_, label, desc) in enumerate(SOURCE_OPTIONS, 1):
        console.print(f"   [cyan]{i}[/cyan]. {label} — {desc}")

    console.print()
    raw_sel = Prompt.ask(
        "   输入编号选择（如 [cyan]1,3,5[/cyan]），直接回车全选",
        default="",
    ).strip()

    if not raw_sel:
        sources = ALL_SOURCES
    else:
        selected = []
        for part in raw_sel.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(SOURCE_OPTIONS):
                    selected.append(SOURCE_OPTIONS[idx][0])
        sources = ",".join(selected) if selected else ALL_SOURCES

    # ── 4. 导出 ───────────────────────────────────────────────────
    export = None
    if Confirm.ask("\n💾 [bold]是否将结果导出到 Markdown 文件？[/bold]", default=False):
        export = Prompt.ask("   文件名", default="results.md")

    console.print()
    return skills, top, sources, export


@click.command()
@click.option(
    "--skills", "-s",
    default=None,
    help="你的技能，用逗号分隔。例如：Python,爬虫,数据可视化（不填则进入交互模式）",
)
@click.option(
    "--top", "-n",
    default=10,
    show_default=True,
    help="返回结果数量",
)
@click.option(
    "--sources",
    default=ALL_SOURCES,
    show_default=True,
    help="数据来源，逗号分隔（可选值：v2ex, sspai, reddit, hn, zhihu）",
)
@click.option(
    "--export",
    type=click.Path(),
    default=None,
    help="导出结果到 Markdown 文件，例如：--export results.md",
)
def main(skills: str | None, top: int, sources: str, export: str | None):
    """SkillMatch：输入技能，发现匹配的产品方向。不带参数直接运行进入交互模式。"""

    # 没有传 -s 时进入交互模式
    if not skills:
        skills_list, top, sources, export = _interactive_prompt()
    else:
        skills_list = [s.strip() for s in skills.split(",") if s.strip()]

    skill_list = skills_list
    source_list = [s.strip().lower() for s in sources.split(",") if s.strip()]

    # ── 标题（非交互模式才打印，交互模式已在 prompt 里打印过了）──────
    if skills:
        console.print()
        console.rule("[bold cyan]⚡ SkillMatch 技能需求匹配[/bold cyan]")
    console.print(
        Panel(
            f"🎯 [bold]技能：[/bold]{' · '.join(skill_list)}\n"
            f"📡 [bold]数据源：[/bold]{', '.join(source_list)}",
            expand=False,
        )
    )

    # ── 抓取数据 ──────────────────────────────────────────────────
    all_posts = []

    if "v2ex" in source_list:
        with console.status("[cyan]获取 V2EX 话题...[/cyan]"):
            posts = fetch_v2ex_posts()
            all_posts.extend(posts)
        console.print(f"  ✅ V2EX：[bold]{len(posts)}[/bold] 条话题")

    if "sspai" in source_list:
        with console.status("[cyan]获取 少数派 文章...[/cyan]"):
            posts = fetch_sspai_posts(skill_list)
            all_posts.extend(posts)
        console.print(f"  ✅ 少数派：[bold]{len(posts)}[/bold] 条文章")

    if "reddit" in source_list:
        with console.status("[cyan]获取 Reddit 帖子...[/cyan]"):
            posts = fetch_reddit_posts()
            all_posts.extend(posts)
        console.print(f"  ✅ Reddit：[bold]{len(posts)}[/bold] 条帖子")

    if "hn" in source_list:
        with console.status("[cyan]获取 Hacker News 帖子...[/cyan]"):
            posts = fetch_hn_posts(skill_list)
            all_posts.extend(posts)
        console.print(f"  ✅ HN：[bold]{len(posts)}[/bold] 条帖子")

    if "zhihu" in source_list:
        with console.status("[cyan]搜索 知乎 问题（通过 DuckDuckGo）...[/cyan]"):
            posts = fetch_zhihu_posts(skill_list)
            all_posts.extend(posts)
        console.print(f"  ✅ 知乎：[bold]{len(posts)}[/bold] 条问题")

    if not all_posts:
        console.print("\n[red]❌ 未能获取任何数据，请检查网络连接后重试。[/red]")
        sys.exit(1)

    console.print(f"\n📊 共 [bold]{len(all_posts)}[/bold] 条内容，正在计算语义匹配度...\n")

    # ── 语义匹配 ──────────────────────────────────────────────────
    with console.status(
        "[cyan]计算语义匹配（首次运行会自动下载模型约 120MB，请稍候）...[/cyan]"
    ):
        matcher = SkillMatcher()
        results = matcher.match(skill_list, all_posts, top_k=top)

    # ── 展示结果 ──────────────────────────────────────────────────
    _display_results(skill_list, results)

    # ── 导出 ──────────────────────────────────────────────────────
    if export:
        _export_markdown(skill_list, results, export)
        console.print(f"\n💾 已导出到 [bold green]{export}[/bold green]")

    console.print()


# ── 展示 ──────────────────────────────────────────────────────────


def _display_results(skills: list[str], results: list[dict]):
    if not results:
        console.print("[yellow]⚠️  未找到匹配结果，尝试增加更多技能标签。[/yellow]")
        return

    table = Table(
        title=f"🔍 为「{'、'.join(skills)}」匹配到的产品方向",
        show_header=True,
        header_style="bold magenta",
        show_lines=True,
        min_width=100,
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("标题 / 痛点", min_width=35)
    table.add_column("来源", width=6, justify="center")
    table.add_column("热度", width=5, justify="right")
    table.add_column("匹配", width=6, justify="center")
    table.add_column("链接", style="cyan dim")

    for i, r in enumerate(results, 1):
        table.add_row(
            str(i),
            r["title"],
            r["source"],
            str(r.get("replies", "-")),
            _score_label(r["score"]),
            r["url"],
        )

    console.print(table)
    console.print(
        "[dim]  💡 匹配度越高 = 该讨论与你的技能越相关，可能藏着值得做的产品机会[/dim]"
    )


def _score_label(score: float) -> str:
    pct = int(score * 100)
    if pct >= 65:
        return f"[bold green]{pct}%[/bold green]"
    elif pct >= 45:
        return f"[yellow]{pct}%[/yellow]"
    else:
        return f"[dim]{pct}%[/dim]"


# ── 导出 ──────────────────────────────────────────────────────────


def _export_markdown(skills: list[str], results: list[dict], filepath: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# SkillMatch 匹配结果\n\n",
        f"**技能**：{', '.join(skills)}  \n",
        f"**生成时间**：{now}\n\n",
        "---\n\n",
    ]
    for i, r in enumerate(results, 1):
        lines.append(f"## {i}. {r['title']}\n\n")
        lines.append(f"- **来源**：{r['source']}\n")
        lines.append(f"- **匹配度**：{int(r['score'] * 100)}%\n")
        lines.append(f"- **热度**：{r.get('replies', '-')} 回复\n")
        lines.append(f"- **链接**：<{r['url']}>\n")
        if r.get("content"):
            lines.append(f"\n> {r['content'][:200]}\n")
        lines.append("\n")

    Path(filepath).write_text("".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
