---
name: awescholar
description: "Use when working with awescholar CLI — scientific literature discovery, annotation, filtering, and report generation. 中文触发词：文献检索、论文搜索、研究报告、awescholar。"
---

# Awescholar

Automated scientific literature discovery and curation CLI.

## Commands

```
awescholar --config PATH crawler run [query]         # full pipeline
awescholar --config PATH crawler search <query>      # search only
awescholar --config PATH crawler annotate [--input]  # annotate papers
awescholar --config PATH crawler filter [--input]    # filter papers
awescholar --config PATH crawler report [input] [-o] # generate report

awescholar updater update --direction new2old|old2new --archive PATH
awescholar updater readme --archive PATH
awescholar updater rss --archive PATH
awescholar updater search --archive PATH [--by title|doi]
awescholar updater add --archive PATH
```

### Step-by-step usage (no need to re-run full pipeline)

Each subcommand accepts `--input` (or positional `input` for report) to read from a specific file instead of the default path. This lets you re-run any step independently:

```bash
# 1. Search → papers.db
awescholar --config cfg.json crawler search "AI agent" --limit 50

# 2. Annotate → updater.json (reads from DB by default, or --input papers.json)
awescholar --config cfg.json crawler annotate
awescholar --config cfg.json crawler annotate --input papers.json

# 3. Filter → updater_filter.json (reads from updater.json by default, or --input)
awescholar --config cfg.json crawler filter --limit 20
awescholar --config cfg.json crawler filter --input my_updater.json

# 4. Report → markdown (reads from updater_filter.json by default, or positional input)
awescholar --config cfg.json crawler report
awescholar --config cfg.json crawler report test/updater_filter.json -o report.md
```

Typical re-run scenarios:
- **Re-generate report only** (no re-search/re-annotate): `awescholar --config cfg.json crawler report updater_filter.json -o report.md`
- **Re-filter with different limit**: `awescholar --config cfg.json crawler filter --input updater.json --limit 10`
- **Re-annotate from JSON** (skip DB): `awescholar --config cfg.json crawler annotate --input papers.json`

## Config (grouped format)

```json
{
    "model": {
        "name": "glm-5.1",
        "api_key": "${ENV}",
        "base_url": "https://open.bigmodel.cn/api/paas/v4"
    },
    "agent_models": null,
    "semantic_scholar": { "api_key": "${SEMANTIC_SCHOLAR_API_KEY}" },
    "search": {
        "query": "AI agent|large language model",
        "fields_of_study": ["Biology", "Medicine"],
        "publication_date": "2025-12-15:2025-12-31",
        "limit": 100, "include_abstracts": true
    },
    "filter": { "limit": 20 },
    "output": { "db_path": "output", "report_filename": null },
    "pipeline": {
        "skip_search": false, "use_updater_json": false,
        "use_filtered_json": false, "merge_new_to_old": false
    },
    "categories": ["Foundation Models", "Drug Discovery", "..."]
}
```

## Key points

- **model.name**: Just the model name, e.g. `glm-5.1`, `deepseek-chat`, `gpt-4o`. The `openai/` prefix is auto-prepended — do NOT add it manually. Only OpenAI-compatible base_url mode is supported (see base_url below).
- **model.base_url**: Required for non-default endpoints. Must point to an **OpenAI-compatible** API (e.g. `https://open.bigmodel.cn/api/paas/v4`). For built-in providers (OpenAI, Anthropic, DeepSeek), can be `null`.
- **agent_models**: Per-agent overrides for annotator/filterer/reporter. `null` = use global. Falls back field-by-field.
- **report output**: Defaults to `{db_path}/research_report_{reporter-model}.md`.
- **pipeline flow control**:
  - `use_filtered_json=true` → skip to report
  - `use_updater_json=true` → skip annotate, do filter + report
  - `skip_search=true` → load from DB, do annotate + filter + report
- **legacy flat config**: Auto-detected and supported.
