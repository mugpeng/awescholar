<div align="center">
  <h1>awescholar: Scientific Literature Curator</h1>
  <p><strong>Automated scientific literature discovery and curation.</strong></p>
  <p>Search, annotate, filter, and report on academic papers — then merge results into your Awesome list.</p>
  <p>
    <strong>English</strong> ·
    <a href="./README_cn.md">简体中文</a>
  </p>
  <p>
    <img src="https://img.shields.io/badge/version-0.1.1-7C3AED?style=flat-square" alt="Version">
    <img src="https://img.shields.io/badge/python-%E2%89%A53.10-0EA5E9?style=flat-square" alt="Python">
  </p>
  <p>
    <img src="https://img.shields.io/badge/status-alpha-c96a3d?style=flat-square" alt="Status">
    <img src="https://img.shields.io/badge/platform-cli-334155?style=flat-square" alt="Platform">
    <img src="https://img.shields.io/github/stars/mugpeng/awescholar?style=flat-square" alt="GitHub stars">
  </p>
</div>

> Search, annotate, filter, and report on academic papers — then merge results into your Awesome list.

A lightweight CLI that automates the paper curation workflow: query Semantic Scholar, annotate with LLM, filter by quality, generate Markdown reports, and incrementally merge into a maintained archive. No agent framework — just Python and an LLM API call.

## Install

```bash
pip install -e .
```

## Quick Start

```bash
# Set API keys (add to ~/.zshrc or ~/.bashrc to persist)
export GLM_API_KEY="sk-..."
export SEMANTICSCHOLAR_API_KEY="your-key"   # optional, without it uses free tier

# Edit config.json to set model name, base_url, search query, etc.

# Run the full pipeline
awescholar --config config.json crawler run

# Or pass query directly
awescholar --config config.json crawler run "perturbation prediction|single cell" --date 2025-01-01:2025-05-30
```

## Config

```json
{
    "model_profiles": {
        "glm": {
            "api_key": "${GLM_API_KEY}",
            "base_url": "https://open.bigmodel.cn/api/paas/v4"
        },
        "deepseek": {
            "api_key": "${DEEPSEEK_API_KEY}",
            "base_url": null
        }
    },
    "model": {
        "profile": "glm",
        "name": "glm-5.1"
    },
    "agent_models": null,
    "semantic_scholar": {
        "api_key": "${SEMANTICSCHOLAR_API_KEY}"
    },
    "search": {
        "query": "AI agent|large language model|foundation model",
        "fields_of_study": ["Biology", "Medicine", "Computer Science"],
        "publication_date": "2025-01-01:2025-05-30",
        "limit": 100,
        "include_abstracts": true
    },
    "filter": {
        "limit": 20,
        "research_interests": null
    },
    "output": {
        "db_path": "output",
        "report_filename": null
    },
    "pipeline": {
        "skip_search": false,
        "use_updater_json": false,
        "use_filtered_json": false,
        "existing_json_path": null,
        "merge_new_to_old": false
    },
    "categories": ["Foundation Models", "Drug Discovery", "Perturbation Study"]
}
```

`${VAR}` patterns are expanded from environment variables at load time. Copy `config.example.json` and fill in your values — or set env vars directly and skip the config file.

**`model.name`** — just the model name, e.g. `glm-5.1`, `deepseek-chat`, `gpt-4o`. The `openai/` prefix is auto-prepended for OpenAI-compatible endpoints — do NOT add it manually.

**`model_profiles`** — reusable profile map. Each profile defines `api_key` and `base_url`. Referenced by `model.profile` or `agent_models.*.profile`, avoiding credential duplication.

**`agent_models`** — override model per agent (annotator, filterer, reporter). Each entry can use `profile` to reference a `model_profiles` entry, or set `name`/`api_key`/`base_url` directly:
```json
"agent_models": {
    "annotator": { "profile": "deepseek", "name": "deepseek-chat" },
    "filterer":  { "profile": "glm", "name": "glm-5.1" },
    "reporter":  { "profile": "glm", "name": "glm-5.1" }
}
```

**`pipeline`** — control flow to skip/reuse intermediate results:
- `skip_search`: load papers from DB instead of searching
- `use_updater_json`: reuse existing `updater.json` (skip search + annotate)
- `use_filtered_json`: reuse existing `updater_filter.json` (skip to report)
- `existing_json_path`: custom path for updater JSON
- `merge_new_to_old`: auto-merge new results into archive after pipeline

**`filter.research_interests`** — optional string describing research focus, passed to filterer for relevance weighting.

**`search.query`** — if set, `crawler run` can be called without a CLI query argument.

Supported LLM providers: any OpenAI-compatible API via `base_url` (e.g. GLM, DeepSeek, Gemini, Mistral, local endpoints).

## Commands

```bash
awescholar -v                                         # Show version

# Paper discovery pipeline
awescholar crawler search "query"                     # Search Semantic Scholar
awescholar crawler annotate                           # Annotate papers in DB
awescholar crawler annotate --input papers.json       # Annotate from JSON (skip DB)
awescholar crawler filter --limit 20                  # Select top papers
awescholar crawler filter --input updater.json        # Filter from custom JSON
awescholar crawler report                             # Generate report (stdout)
awescholar crawler report updater_filter.json -o report.md  # Report from custom JSON
awescholar crawler run ["query"]                      # Full pipeline (query optional if set in config)

# Archive management
awescholar updater update --direction new2old --archive data.json   # Merge to archive
awescholar updater readme --archive data.json         # Generate README tables
awescholar updater rss --archive data.json            # Generate RSS feed
awescholar updater search --archive data.json --by title           # Search by title and add
awescholar updater add --archive data.json            # Interactively add a record
```

Each subcommand accepts `--input` (or positional `input` for report) to read from a specific file instead of the default path. This lets you re-run any step independently without re-running the full pipeline.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Workflow

```
crawler search -> crawler annotate -> crawler filter -> crawler report
                                                        |
                                                        v
                                              updater_filter.json
                                                        |
                                              updater update new2old
                                                        |
                                                        v
                                              archive.json -> updater readme / updater rss
```

Each step produces a JSON intermediate file. You can re-run any step independently.
