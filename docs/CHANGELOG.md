# Changelog

## v0.1.3

Config module extraction, auto-merge pipeline, and filter limit fix.

### Highlights

- Extract `config.py` module — `load_config`, `prefix_model`, `resolve_agent_settings` moved out of `cli.py` for reuse and testability
- `pipeline.data_json_path` — auto-merge filtered results into project data JSON after pipeline completes
- `updater search --json-file` — save search results to flat JSON for review before merging into project data
- `updater readme --no-backup` — skip timestamped README backup creation
- Fix: filter now respects `limit` by truncating in LLM ranking order (previously kept all papers)
- Add ruff as dev dependency (`py310`, `line-length = 100`)
- Add install and PyPI downloads badges to README
- Terminology: "archive" → "project data JSON" across docs and CLI help
- New tests: config loading, agent resolution, CLI help/version, pipeline auto-merge

## v0.1.2

Model profiles, research interests filter, and PyPI publish fix.

### Highlights

- `model_profiles` — named LLM provider presets (api_key + base_url) referenced by `profile` field in `model` and `agent_models`, so switching providers only requires changing one field
- `research_interests` in `filter` config — user-defined interests passed to the filterer for priority-based selection
- `--input` flags on `annotate`, `filter`, `report` subcommands for step reuse without re-running earlier stages
- Reporter prompt: enforce consecutive global index, every paper must appear in report
- Filter prompt: quality-first priority, then relevance to research interests
- PyPI publish switched from OIDC (`pypa/gh-action-pypi-publish`) to `twine upload` with API token
- `config.example.json` updated with `model_profiles` usage

## v0.1.1

CLI restructure, grouped config format, and new single-record commands.

### Highlights

- Group CLI commands into `crawler` (search, annotate, filter, report, run) and `updater` (update, readme, rss, search, add)
- Grouped config format: `model`, `search`, `filter`, `output`, `pipeline`, `agent_models`
- `agent_models` — override LLM model per agent (annotator, filterer, reporter)
- Pipeline flow control: `skip_search`, `use_updater_json`, `use_filtered_json`
- `search.query` in config allows `crawler run` without CLI query argument
- `awescholar updater search` — search Semantic Scholar by title/DOI and add to archive
- `awescholar updater add` — interactively add a single record to archive
- Document `fields_of_study` valid values (23 fields) in search module
- Add Chinese README (README_cn.md), CONTRIBUTING.md, CI/CD workflows
- Add "Scientific Literature Curator" subtitle to README

## v0.1.0

Initial release. Simplified rewrite of AweAgent without agent framework dependency.

### Highlights

- Pure Python + LiteLLM — no Agno or other agent framework
- 4-step pipeline: search, annotate, filter, report
- Semantic Scholar integration with SQLite deduplication
- Incremental merge for maintaining curated Awesome lists
- README table generation and RSS feed from archive JSON
- Multi-provider LLM support via LiteLLM (OpenAI, DeepSeek, Gemini, Mistral)
- Config via JSON file with `${ENV_VAR}` expansion or direct environment variables
