# SkillMatch ⚡

> 输入你的技能，自动发现「我能做、有人要」的产品方向

从 V2EX、少数派等开发者社区抓取真实讨论，用语义匹配算法找出与你技能最相关的需求和痛点。

## 快速开始

### 1. 安装依赖

```bash
cd skillmatch
pip install -r requirements.txt
```

> 首次运行会自动下载语义模型（约 120MB），之后复用本地缓存。

### 2. 运行

```bash
# 基础用法
python main.py -s "Python,爬虫,数据可视化"

# 指定返回数量
python main.py -s "UI设计,Figma" --top 5

# 只搜某个数据源
python main.py -s "Python" --sources v2ex

# 导出结果到 Markdown
python main.py -s "Python,机器学习" --export results.md
```

### 参数说明

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--skills` | `-s` | 技能标签，逗号分隔 | 必填 |
| `--top` | `-n` | 返回结果数量 | 10 |
| `--sources` | - | 数据源（v2ex, sspai, reddit, hn） | v2ex,sspai,reddit,hn |
| `--export` | - | 导出 Markdown 文件路径 | 不导出 |

## 数据源

| 来源 | 接口 | 更新频率 | 缓存时长 |
|------|------|---------|---------|
| V2EX | 官方公开 API | 实时 | 2 小时 |
| 少数派 | 公开 Tag API | 实时 | 不缓存 |
| Reddit | 公开 JSON 接口（无需 Key） | 近一周热帖 | 2 小时 |
| HN | Algolia 搜索 API（无需 Key） | 2025 年以来 | 不缓存 |
| 知乎 | DuckDuckGo 搜索 site:zhihu.com/question | 实时索引 | 不缓存 |

## 目录结构

```
skillmatch/
├── main.py          # 入口，CLI 命令
├── matcher.py       # 语义匹配引擎
├── fetchers/
│   ├── v2ex.py      # V2EX 数据获取
│   └── sspai.py     # 少数派数据获取
├── cache/           # 本地缓存（自动生成）
└── requirements.txt
```

## 后续计划（V2）

- [ ] Web UI 界面
- [ ] Reddit / Hacker News 数据源
- [ ] 知乎数据源
- [ ] 结果持久化与历史对比
- [ ] 定时任务 + 邮件推送
