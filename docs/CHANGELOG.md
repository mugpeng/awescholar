# Changelog

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
