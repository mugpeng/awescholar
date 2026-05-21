<div align="center">
  <h1>awescholar: Scientific Literature Curator</h1>
  <p><strong>Automated scientific literature discovery and curation.</strong></p>
  <p>Search, annotate, filter, and report on academic papers — then merge results into your Awesome list.</p>
  <p>
    <strong>English</strong> ·
    <a href="./README_cn.md">简体中文</a>
  </p>
  <p>
    <img src="https://img.shields.io/badge/version-0.1.0-7C3AED?style=flat-square" alt="Version">
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
# Set your LLM provider
export AWESCHOLAR_MODEL="gpt-4.1-mini"
export AWESCHOLAR_API_KEY="sk-..."

# Run the full pipeline
awescholar crawler run "perturbation prediction|single cell" --date 2025-01-01:2025-05-30

# Or use a config file
awescholar --config config.json crawler run "foundation model" --date 2025-01-01:2025-05-30
```

## Config

```json
{
    "model": "${AWESCHOLAR_MODEL}",
    "api_key": "${AWESCHOLAR_API_KEY}",
    "base_url": "${AWESCHOLAR_BASE_URL}",
    "ss_api_key": "${SEMANTICSCHOLAR_API_KEY}",
    "db_path": "output",
    "limit_search": 100,
    "limit_filter": 20,
    "categories": ["Foundation Models", "Drug Discovery", "Perturbation Study"],
    "fields_of_study": ["Biology", "Medicine"],
    "publication_date": "2025-01-01:2025-05-30"
}
```

`${VAR}` patterns are expanded from environment variables at load time. Copy `config.example.json` and fill in your values — or set env vars directly and skip the config file.

Supported LLM providers (via LiteLLM): OpenAI, DeepSeek, Gemini, Mistral, custom endpoints.

## Commands

```bash
awescholar -v                                         # Show version

# Paper discovery pipeline
awescholar crawler search "query"                     # Search Semantic Scholar
awescholar crawler annotate                           # Annotate papers in DB
awescholar crawler filter --limit 20                  # Select top papers
awescholar crawler report -o report.md                # Generate Markdown report
awescholar crawler run "query"                        # Full pipeline

# Archive management
awescholar updater update --direction new2old --archive data.json   # Merge to archive
awescholar updater readme --archive data.json         # Generate README tables
awescholar updater rss --archive data.json            # Generate RSS feed
awescholar updater search --archive data.json --by title           # Search by title and add
awescholar updater add --archive data.json            # Interactively add a record
```

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
