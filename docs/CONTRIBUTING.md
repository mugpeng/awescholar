# Contributing

## Development Setup

```bash
git clone https://github.com/Webioinfo01/awescholar.git
cd awescholar
pip install -e ".[dev]"
pytest
```

Requires Python >= 3.10.

## Project Structure

```
src/awescholar/
  __init__.py       # Version
  cli.py            # CLI wiring, config loading, argument parsing
  pipeline.py       # Step orchestration: search -> annotate -> filter -> report
  search.py         # Semantic Scholar API client
  llm.py            # LiteLLM completion wrapper
  prompts.py        # System prompt strings
  schemas.py        # Pydantic models for annotation and filtering
  db.py             # SQLAlchemy ORM (Paper model) and session factory
  utils.py          # Merge, README generation, RSS generation
tests/
  test_db.py        # DB and Paper model tests
  test_schemas.py   # Pydantic schema tests
  test_utils.py     # Merge, README, RSS utility tests
```

Separation: `cli.py` handles I/O and config. `pipeline.py` orchestrates steps. Other modules handle domain logic.

## Architecture

**4-step pipeline** — each step is a pure function that takes input and returns output:

1. **Search** — Query Semantic Scholar API, deduplicate against SQLite DB
2. **Annotate** — LLM classifies papers by domain and category
3. **Filter** — LLM selects top N papers by quality and relevance
4. **Report** — LLM generates a Markdown summary

Steps are composable. Run the full pipeline with `awescholar run` or individual steps.

**Data flow**: Each step reads/writes JSON files (`updater.json`, `updater_filter.json`, `report.md`). Re-run any step independently.

**Merge model**: `updater update --direction new2old` merges new results into a persistent archive. `old2new` enriches new results with archive data.

## Data Model

`Paper` (SQLAlchemy) — stores raw search results with deduplication by `paper_id`.

`PaperAnnotation` / `FilteredPaper` (Pydantic) — structured LLM output for annotation and filtering stages.

## Config

Config uses `${ENV_VAR}` expansion. Sensitive values (API keys) must use `${VAR}` syntax in `config.example.json`, never hardcoded. The CLI resolves these from environment variables at load time.

Top-level keys: `model_profiles`, `model`, `agent_models`, `semantic_scholar`, `search`, `filter`, `output`, `pipeline`, `categories`.

**`model_profiles`**: reusable profile map — each profile defines `api_key` and `base_url`. Referenced by `model.profile` or `agent_models.*.profile`.

**`model.name`**: just the model name (e.g. `glm-5.1`). The `openai/` prefix is auto-prepended by `_prefix_model()`.

**`agent_models`**: per-agent model overrides for annotator, filterer, reporter. Each entry can use `profile` to reference `model_profiles`. Falls back to global `model` config if not set.

**`filter.research_interests`**: optional string for relevance weighting during filtering.

**`pipeline`**: flow control flags — `skip_search`, `use_updater_json`, `use_filtered_json`, `existing_json_path`, `merge_new_to_old`. Allows reusing intermediate JSON files to skip pipeline steps.

**`search.query`**: if set, `crawler run` can omit the CLI query argument.

## Code Style

- Functional over OOP — no classes except SQLAlchemy models and Pydantic schemas
- Functions are pure where possible; side effects (I/O, API calls) are isolated
- Error messages are user-facing and actionable
- Imports: stdlib first, blank line, then third-party

## Testing

```bash
pytest
```

One test file per source module. Tests use real SQLite databases (in-memory or temp files), no filesystem mocking.

## Branch Model

- `main` — stable, always deployable
- Feature branches: `feat/short-description`
- Fix branches: `fix/short-description`

## Release Workflow

1. Update `docs/CHANGELOG.md` with version notes
2. Update version in `pyproject.toml` and `src/awescholar/__init__.py`
3. Tag: `git tag vX.Y.Z && git push origin vX.Y.Z`
4. CI creates GitHub Release and publishes to PyPI

## Pull Requests

- One logical change per PR
- Include tests for new functionality
- Update docs if behavior changes
- Reference related issues
