[简体中文](./README.zh-CN.md) | [English](./README.md)

# 📚 Paper Agent

自动化学术论文推送 + 搜索系统。支持定时推送和主动搜索两种模式，GPT 生成中文摘要，通过邮件推送或在 Web UI 中直接浏览结果。

## 功能

### 推送模式（Push Mode）
- **定时推送**：每周一/周四早 8 点自动推送（可配置）
- **手动推送**：通过 Web UI 或 GitHub Actions 手动触发
- **多 Profile**：支持多个搜索方向同时运行
- **三级数据源**：Semantic Scholar + OpenReview + OpenAlex
- **智能去重**：跨数据源去重 + 历史去重，不会重复推送
- **GPT 摘要**：自动生成中文总结和推荐理由
- **语义重排（Embedding Reranking）**：用 OpenAI Embedding 对论文做语义相似度排序，找到关键词搜不到但语义相关的论文
- **起始年份**：每个 Profile 可设定 `year_from`，只检索该年份之后的论文
- **Venue 分组**：可指定只看顶会/顶刊论文，或不限但优先展示 top venue

### 搜索模式（Search Mode）
- **Web UI 直接搜索**：在浏览器中实时检索三大数据源
- **关键词组**：支持手动编辑或 GPT 自动生成多组关键词
- **Venue 分组筛选**：搜索结果可按 venue 分组过滤或优先排序
- **起始年份**：可设定只搜索某年之后的论文
- **搜索 Profile**：保存常用的搜索配置，一键加载

## 快速开始

### 1. Fork 或 Clone 仓库

```bash
git clone https://github.com/YOUR_USERNAME/paper-agent.git
cd paper-agent
```

### 2. 配置 GitHub Secrets

在仓库的 **Settings → Secrets and variables → Actions** 中添加：

| Secret Name | 说明 |
|---|---|
| `OPENAI_API_KEY` | OpenAI API Key |
| `GMAIL_ADDRESS` | 发送邮件的 Gmail 地址 |
| `GMAIL_APP_PASSWORD` | Gmail App Password（非登录密码） |

#### 获取 Gmail App Password

1. 访问 [Google Account → Security](https://myaccount.google.com/security)
2. 开启 **两步验证**
3. 在两步验证页面底部找到 **App Passwords**
4. 选择 "Mail" + "Other (Custom name)"，输入 "Paper Agent"
5. 复制生成的 16 位密码

### 3. 编辑 config.json

修改 `config.json` 中的 profiles 和设置：

```json
{
  "push_profiles": [
    {
      "id": "my_topic",
      "name": "我的研究方向",
      "query": "用自然语言描述你想找什么论文",
      "sources": ["semantic_scholar", "openalex", "openreview"],
      "venue_filter": "top_cs_conference",
      "count": 5,
      "year_from": 2023,
      "active": true
    }
  ],
  "search_profiles": [
    {
      "id": "my_search",
      "name": "我的搜索方向",
      "query": "搜索描述",
      "keyword_groups": [["keyword1", "keyword2"], ["keyword3", "keyword4"]],
      "sources": ["semantic_scholar", "openalex", "openreview"],
      "venue_filter": "any",
      "max_per_group": 25,
      "year_from": 2024
    }
  ],
  "global": {
    "email": "your-email@gmail.com"
  }
}
```

### 4. 启用 GitHub Pages（可选，用于 Web UI）

1. **Settings → Pages**
2. Source 选择 **Deploy from a branch**
3. Branch 选择 `main`，文件夹选择 `/docs`
4. 保存后访问 `https://YOUR_USERNAME.github.io/paper-agent/`

### 5. 配置 Web UI

1. 打开 Web UI 页面
2. 在 GitHub 连接区域填入：
   - Repository Owner（你的 GitHub 用户名）
   - Repository Name（`paper-agent`）
   - Personal Access Token（需要 `repo` 和 `actions:write` 权限）
3. 点击「保存并连接」

#### 创建 Personal Access Token

1. [GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens](https://github.com/settings/tokens?type=beta)
2. 选择目标仓库
3. 权限勾选：`Contents: Read and Write` + `Actions: Read and Write`
4. 生成并复制 Token

## 使用方式

### 自动推送
配置完成后，GitHub Actions 会按 cron 计划自动执行。

### 手动推送（Web UI）
打开 Web UI → 选择 Profile 或输入临时查询 → 点击「立即推送」

### 手动推送（GitHub）
仓库 → Actions → Paper Agent Push → Run workflow → 填入参数 → 运行

### 手动推送（本地运行）
```bash
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."
export GMAIL_ADDRESS="your@gmail.com"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
python src/main.py
```

### Web UI 搜索
打开 Web UI → 切换到「搜索」面板 → 输入查询或加载搜索 Profile → 选择 Venue 分组和起始年份 → 点击「开始搜索」

## Profile 配置

### 推送 Profile（push_profiles）

| 字段 | 说明 |
|---|---|
| `id` | 唯一标识 |
| `name` | 显示名称 |
| `query` | 自然语言搜索描述（GPT 会自动解析成关键词） |
| `sources` | 数据源列表（`semantic_scholar`、`openalex`、`openreview`） |
| `venue_filter` | Venue 分组名（见下表） |
| `count` | 每次推送的目标论文数量 |
| `year_from` | 起始年份，只检索该年份及之后的论文（可选） |
| `active` | 是否启用 |

### 搜索 Profile（search_profiles）

| 字段 | 说明 |
|---|---|
| `id` | 唯一标识 |
| `name` | 显示名称 |
| `query` | 自然语言搜索描述 |
| `keyword_groups` | 关键词组（每组为一个字符串数组） |
| `sources` | 数据源列表 |
| `venue_filter` | Venue 分组名（见下表） |
| `max_per_group` | 每组关键词最大检索数量 |
| `year_from` | 起始年份（可选） |

## Venue 分组

| 分组 | 包含 |
|---|---|
| `top_cs_conference` | ICLR, NeurIPS, ICML, ACL, EMNLP, CVPR, KDD, AAAI |
| `top_construction_journal` | Automation in Construction, Advanced Engineering Informatics, J. Computing in Civil Eng., Building and Environment, J. Constr. Eng. Mgmt., Engineering Structures |
| `any` | 不限制 venue（但优先展示来自 top venue 的论文） |

可在 `config.json` 的 `venue_groups` 中自由添加新分组。

## 项目结构

```text
paper-agent/
├── config.json              # 搜索配置（profiles, venues, settings）
├── history.json             # 推送历史（防重复）
├── requirements.txt
├── src/
│   ├── main.py              # 主流程
│   ├── query_parser.py      # GPT 意图解析
│   ├── summarizer.py        # GPT 筛选 + 中文摘要
│   ├── reranker.py          # Embedding 语义重排
│   ├── dedup.py             # 跨源 + 历史去重
│   ├── email_sender.py      # Gmail SMTP + HTML 模板
│   ├── utils.py             # 工具函数
│   └── search/
│       ├── base.py          # Paper 数据结构
│       ├── semantic_scholar.py
│       ├── openreview.py
│       ├── openalex.py
│       └── router.py        # 智能数据源路由 + venue 优先级
├── docs/                    # GitHub Pages 前端（Web UI）
│   ├── index.html
│   ├── style.css
│   └── app.js
└── .github/workflows/
    └── push.yml             # 定时 + 手动触发
```

## GPT 模型

| 环境变量 | 默认值 | 用途 |
|---|---|---|
| `GPT_MODEL_KEYWORD` | `gpt-5.4` | 关键词解析 |
| `GPT_MODEL_SUMMARY` | `gpt-5.4-mini` | 论文筛选 + 中文摘要生成 |

可通过 GitHub Secrets 中设置对应环境变量来修改模型。

## License

MIT
