#!/usr/bin/env python3
"""
SkillMatch - 技能 × 需求自动匹配工具

输入你的技能，自动扫描开发者社区的真实讨论，
找到「我能做、有人要」的产品方向。

用法示例：
  python main.py -s "Python,爬虫,数据可视化"
  python main.py -s "UI设计,Figma,交互设计" --top 5
  python main.py -s "Python,机器学习" --export results.md
  python main.py -s "Python" --sources v2ex         # 只搜 V2EX
"""

import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from fetchers.v2ex import fetch_v2ex_posts
from fetchers.sspai import fetch_sspai_posts
from fetchers.reddit import fetch_reddit_posts
from fetchers.hn import fetch_hn_posts
from fetchers.zhihu import fetch_zhihu_posts
from matcher import SkillMatcher

console = Console()


@click.command()
@click.option(
    "--skills", "-s",
    required=True,
    help="你的技能，用逗号分隔。例如：Python,爬虫,数据可视化",
)
@click.option(
    "--top", "-n",
    default=10,
    show_default=True,
    help="返回结果数量",
)
@click.option(
    "--sources",
    default="v2ex,sspai,reddit,hn,zhihu",
    show_default=True,
    help="数据来源，逗号分隔（可选值：v2ex, sspai, reddit, hn, zhihu）",
)
@click.option(
    "--export",
    type=click.Path(),
    default=None,
    help="导出结果到 Markdown 文件，例如：--export results.md",
)
def main(skills: str, top: int, sources: str, export: str | None):
    """SkillMatch：输入技能，发现匹配的产品方向"""

    skill_list = [s.strip() for s in skills.split(",") if s.strip()]
    source_list = [s.strip().lower() for s in sources.split(",") if s.strip()]

    # ── 标题 ──────────────────────────────────────────────────────
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
