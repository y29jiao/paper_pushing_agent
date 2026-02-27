# 📚 Paper Agent

自动化学术论文推送系统。定时检索论文，GPT 生成中文摘要，通过邮件推送。

## 功能

- **定时推送**：每周一/周四早 8 点自动推送（可配置）
- **主动推送**：通过 Web UI 或 GitHub Actions 手动触发
- **多 Profile**：支持多个搜索方向同时运行（如 AI + Construction）
- **三级数据源**：Semantic Scholar + OpenReview + OpenAlex
- **智能去重**：跨数据源去重 + 历史去重，不会重复推送
- **GPT 摘要**：自动生成中文总结和推荐理由

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
  "profiles": [
    {
      "id": "my_topic",
      "name": "我的研究方向",
      "query": "用自然语言描述你想找什么论文",
      "sources": ["semantic_scholar", "openreview", "openalex"],
      "venue_filter": "top_ai",
      "count": 5,
      "active": true
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
3. Branch 选择 `main`，文件夹选择 `/web`（或将 web 内容放在 `/docs`）
4. 保存后访问 `https://YOUR_USERNAME.github.io/paper-agent/`

> **注意**：GitHub Pages 默认从 root 或 `/docs` 部署。如需从 `/web` 部署，
> 可将 web 文件夹重命名为 `docs`，或使用 GitHub Actions 部署 Pages。

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

## Venue 分组

| 分组 | 包含 |
|---|---|
| `top_ai` | ICLR, NeurIPS, ICML, ACL, EMNLP, CVPR, KDD, AAAI |
| `construction` | Automation in Construction, Advanced Engineering Informatics, J. Computing in Civil Eng., Building and Environment, J. Constr. Eng. Mgmt., Engineering Structures |
| `any` | 不限制 venue |

可在 `config.json` 的 `venue_groups` 中自由添加新分组。

## 项目结构

```
paper-agent/
├── config.json              # 搜索配置（profiles, venues, settings）
├── history.json             # 推送历史（防重复）
├── requirements.txt
├── src/
│   ├── main.py              # 主流程
│   ├── query_parser.py      # GPT 意图解析
│   ├── summarizer.py        # GPT 筛选 + 中文摘要
│   ├── dedup.py             # 跨源 + 历史去重
│   ├── email_sender.py      # Gmail SMTP + HTML 模板
│   ├── utils.py             # 工具函数
│   └── search/
│       ├── base.py          # Paper 数据结构
│       ├── semantic_scholar.py
│       ├── openreview.py
│       ├── openalex.py
│       └── router.py        # 智能数据源路由
├── web/                     # GitHub Pages 前端
│   ├── index.html
│   ├── style.css
│   └── app.js
└── .github/workflows/
    └── push.yml             # 定时 + 手动触发
```

## GPT 模型

默认使用 `gpt-5.2`。可通过 GitHub Secret `GPT_MODEL` 修改，例如设为 `gpt-4o` 或 `gpt-4o-mini`。

## License

MIT
