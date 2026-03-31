[简体中文](./README.md) | [English](./README.en.md)

# 📚 Paper Agent

An automated academic paper push + search system. It supports both scheduled push and active search workflows, uses GPT to generate Chinese summaries, and lets you receive results by email or browse them directly in the Web UI.

## Features

### Push Mode
- **Scheduled push**: automatically push papers every Monday/Thursday at 8:00 AM by default
- **Manual push**: trigger from the Web UI or GitHub Actions
- **Multiple profiles**: run multiple research directions at the same time
- **Three data sources**: Semantic Scholar + OpenReview + OpenAlex
- **Smart deduplication**: cross-source dedup + history dedup to avoid repeated pushes
- **GPT summaries**: automatically generate Chinese summaries and recommendation reasons
- **Semantic reranking**: use OpenAI embeddings to rerank papers by semantic similarity
- **Year filter**: each profile can define `year_from`
- **Venue grouping**: restrict to top venues or keep all venues while prioritizing top ones

### Search Mode
- **Direct Web UI search**: search the three sources in the browser
- **Keyword groups**: manually edit keyword groups or generate them with GPT
- **Venue filtering**: filter or prioritize results by venue group
- **Year filter**: search only papers after a given year
- **Search profiles**: save and reuse common search settings

## Quick Start

### 1. Fork or clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/paper-agent.git
cd paper-agent
```

### 2. Configure GitHub Secrets

Add these secrets in **Settings → Secrets and variables → Actions**:

| Secret Name | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `GMAIL_ADDRESS` | Gmail address used to send email |
| `GMAIL_APP_PASSWORD` | Gmail App Password, not your login password |

#### How to get a Gmail App Password

1. Go to [Google Account → Security](https://myaccount.google.com/security)
2. Turn on **2-Step Verification**
3. Find **App Passwords**
4. Choose `Mail` + `Other (Custom name)` and enter `Paper Agent`
5. Copy the generated 16-character password

### 3. Edit `config.json`

Update the profiles and settings in `config.json`:

```json
{
  "push_profiles": [
    {
      "id": "my_topic",
      "name": "My Research Topic",
      "query": "Describe what kind of papers you want in natural language",
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
      "name": "My Search Topic",
      "query": "Search description",
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

### 4. Enable GitHub Pages (optional, for the Web UI)

1. Open **Settings → Pages**
2. Set Source to **Deploy from a branch**
3. Select branch `main` and folder `/docs`
4. Save and visit `https://YOUR_USERNAME.github.io/paper-agent/`

### 5. Configure the Web UI

1. Open the Web UI page
2. Fill in the GitHub connection section:
   - Repository Owner
   - Repository Name (`paper-agent`)
   - Personal Access Token (requires `repo` and `actions:write`)
3. Click **Save & Connect**

#### Create a Personal Access Token

1. Open [GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens](https://github.com/settings/tokens?type=beta)
2. Select the target repository
3. Grant `Contents: Read and Write` and `Actions: Read and Write`
4. Generate and copy the token

## Usage

### Scheduled push
Once configured, GitHub Actions will run automatically according to the cron schedule.

### Manual push from Web UI
Open the Web UI → choose a profile or enter a temporary query → click the push button

### Manual push from GitHub
Repository → Actions → Paper Agent Push → Run workflow → fill parameters → run

### Manual push locally

```bash
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."
export GMAIL_ADDRESS="your@gmail.com"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
python src/main.py
```

### Web UI search
Open the Web UI → switch to the Search panel → enter a query or load a search profile → choose a venue group and year filter → click Search

## Profile Configuration

### Push profile (`push_profiles`)

| Field | Description |
|---|---|
| `id` | Unique identifier |
| `name` | Display name |
| `query` | Natural-language search request |
| `sources` | Data source list (`semantic_scholar`, `openalex`, `openreview`) |
| `venue_filter` | Venue group name |
| `count` | Number of papers to push each time |
| `year_from` | Optional lower bound for publication year |
| `active` | Whether the profile is enabled |

### Search profile (`search_profiles`)

| Field | Description |
|---|---|
| `id` | Unique identifier |
| `name` | Display name |
| `query` | Natural-language search request |
| `keyword_groups` | Keyword groups, each as an array of strings |
| `sources` | Data source list |
| `venue_filter` | Venue group name |
| `max_per_group` | Max papers to fetch per keyword group |
| `year_from` | Optional lower bound for publication year |

## Venue Groups

| Group | Includes |
|---|---|
| `top_cs_conference` | ICLR, NeurIPS, ICML, ACL, EMNLP, CVPR, KDD, AAAI |
| `top_construction_journal` | Automation in Construction, Advanced Engineering Informatics, J. Computing in Civil Eng., Building and Environment, J. Constr. Eng. Mgmt., Engineering Structures |
| `any` | No hard venue restriction, but top venues are prioritized |

You can add more venue groups in `config.json`.

## Project Structure

```text
paper-agent/
├── config.json              # Search config (profiles, venues, settings)
├── history.json             # Push history (dedup)
├── requirements.txt
├── src/
│   ├── main.py              # Main workflow
│   ├── query_parser.py      # GPT query parsing
│   ├── summarizer.py        # GPT filtering + Chinese summaries
│   ├── reranker.py          # Embedding-based reranking
│   ├── dedup.py             # Cross-source + history dedup
│   ├── email_sender.py      # Gmail SMTP + HTML template
│   ├── utils.py             # Utility helpers
│   └── search/
│       ├── base.py          # Paper data structure
│       ├── semantic_scholar.py
│       ├── openreview.py
│       ├── openalex.py
│       └── router.py        # Source routing + venue priority
├── docs/                    # GitHub Pages frontend (Web UI)
│   ├── index.html
│   ├── style.css
│   └── app.js
└── .github/workflows/
    └── push.yml             # Scheduled + manual workflow
```

## GPT Models

| Environment Variable | Default | Purpose |
|---|---|---|
| `GPT_MODEL_KEYWORD` | `gpt-5.4` | Keyword parsing |
| `GPT_MODEL_SUMMARY` | `gpt-5.4-mini` | Paper filtering + Chinese summary generation |

You can override these through GitHub Secrets.

## License

MIT
