---
name: awescholar
description: "Use when working with awescholar CLI — scientific literature discovery, annotation, filtering, and report generation. 中文触发词：文献检索、论文搜索、研究报告、awescholar。"
---

# Awescholar

Automated scientific literature discovery and curation CLI.

## Commands

```
awescholar crawler run [query]  --config PATH  # full pipeline
awescholar crawler search <query> [--limit N] [--date RANGE]
awescholar crawler annotate
awescholar crawler filter [--limit N]
awescholar crawler report [-o PATH]

awescholar updater update --direction new2old|old2new --archive PATH
awescholar updater readme --archive PATH
awescholar updater rss --archive PATH
awescholar updater search --archive PATH [--by title|doi]
awescholar updater add --archive PATH
```

## Config (grouped format)

```json
{
    "model": { "name": "openai/glm-5.1", "api_key": "${ENV}", "base_url": null },
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

- **model**: LiteLLM format. Use `openai/model-name` prefix for OpenAI-compatible APIs.
- **agent_models**: Per-agent overrides for annotator/filterer/reporter. `null` = use global. Falls back field-by-field.
- **report output**: Defaults to `{db_path}/research_report_{reporter-model}.md`.
- **pipeline flow control**:
  - `use_filtered_json=true` → skip to report
  - `use_updater_json=true` → skip annotate, do filter + report
  - `skip_search=true` → load from DB, do annotate + filter + report
- **legacy flat config**: Auto-detected and supported.
