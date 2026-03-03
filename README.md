# SkillMatch ⚡

> 输入你的技能，自动发现「我能做、有人要」的产品方向

从 V2EX、少数派、知乎、Reddit、HN 抓取真实社区讨论，
用语义匹配算法找出与你技能最相关的需求和痛点。

## 快速开始

### 1. 下载项目

```bash
git clone https://github.com/Alexkkk76/skillmatch-.git
cd skillmatch-
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

> 首次运行会自动下载语义模型（约 120MB），之后复用本地缓存。

### 3. 运行

**交互模式**（推荐新手）：

```bash
python main.py
```

直接运行，按提示逐步输入技能、结果数量、数据源。

**命令行模式**：

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

## 参数说明

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--skills` | `-s` | 技能标签，逗号分隔 | 必填 |
| `--top` | `-n` | 返回结果数量 | 10 |
| `--sources` | - | 数据源，逗号分隔 | v2ex,sspai,reddit,hn,zhihu |
| `--export` | - | 导出 Markdown 文件路径 | 不导出 |

## 数据源

| 来源 | 接口 | 缓存 |
|------|------|------|
| V2EX | 官方公开 API | 2 小时 |
| 少数派 | 公开 Tag API | 无 |
| Reddit | 公开 JSON 接口（无需 Key） | 2 小时 |
| HN | Algolia 搜索 API（无需 Key） | 无 |
| 知乎 | DuckDuckGo 搜索索引（无需 Key） | 无 |

## 目录结构

```
skillmatch/
├── main.py          # 入口，CLI 命令
├── matcher.py       # 语义匹配引擎
├── fetchers/
│   ├── v2ex.py      # V2EX 数据获取
│   ├── sspai.py     # 少数派数据获取
│   ├── reddit.py    # Reddit 数据获取
│   ├── hn.py        # Hacker News 数据获取
│   └── zhihu.py     # 知乎数据获取
├── cache/           # 本地缓存（自动生成）
└── requirements.txt
```

## 后续计划

- [ ] Web UI 界面
- [ ] 结果持久化与历史对比
- [ ] 定时推送匹配报告
