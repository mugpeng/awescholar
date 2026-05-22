"""Core pipeline: search -> annotate -> filter -> report."""

import json
import os
from typing import Callable

from . import prompts
from .llm import complete
from .schemas import AnnotationResult, FilterResult
from .search import search_papers

StatusCallback = Callable[[str], None] | None


def _noop(msg: str) -> None:
    pass


def run_search(
    query: str,
    db_path: str = "output",
    api_key: str | None = None,
    limit: int = 100,
    fields_of_study: list[str] | None = None,
    publication_date_or_year: str | None = None,
    status_cb: StatusCallback = None,
) -> list[dict]:
    """Search Semantic Scholar and save to DB. Returns paper dicts."""
    cb = status_cb or _noop
    cb(f"Searching Semantic Scholar (limit={limit})...")
    papers = search_papers(
        query=query,
        db_path=db_path,
        api_key=api_key,
        limit=limit,
        fields_of_study=fields_of_study,
        publication_date_or_year=publication_date_or_year,
    )
    cb(f"Found {len(papers)} papers.")
    return papers


def run_annotate(
    papers: list[dict],
    model: str,
    categories: list[str] | None = None,
    include_abstracts: bool = True,
    api_key: str | None = None,
    base_url: str | None = None,
    status_cb: StatusCallback = None,
) -> dict[str, list[dict]]:
    """Annotate papers with domain and category. Returns structured dict by category."""
    cb = status_cb or _noop
    cb("Annotating papers...")

    cat_str = json.dumps(categories) if categories else "[]"
    papers_xml = "<papers>\n"
    for p in papers:
        abstract_part = f"\n  <abstract>{p.get('abstract', '')}</abstract>" if include_abstracts else ""
        papers_xml += f"<paper>\n  <doi>{p['doi']}</doi>\n  <title>{p['title']}</title>{abstract_part}\n</paper>\n"
    papers_xml += f"</papers>\n<predefined_category_list>\n{cat_str}\n</predefined_category_list>"

    result = complete(
        model=model, system=prompts.ANNOTATOR, user=papers_xml,
        response_format=AnnotationResult, api_key=api_key, base_url=base_url,
    )
    if isinstance(result, str):
        result = complete(
            model=model, system=prompts.ANNOTATOR, user=papers_xml,
            response_format=AnnotationResult, api_key=api_key, base_url=base_url,
        )
        if isinstance(result, str):
            raise RuntimeError(f"Annotator LLM returned invalid response. Raw: {result[:200]}")

    paper_map = {p["doi"]: p for p in papers}
    structured: dict[str, list[dict]] = {}
    for ann in result.paper_list:
        paper_data = paper_map.get(ann.doi)
        if not paper_data:
            continue
        entry = {**paper_data, "domain": ann.domain, "category": ann.category}
        structured.setdefault(ann.category, []).append(entry)

    cb(f"Annotated {len(result.paper_list)} papers into {len(structured)} categories.")
    return structured


def run_filter(
    structured_data: dict[str, list[dict]],
    model: str,
    limit: int = 20,
    api_key: str | None = None,
    base_url: str | None = None,
    status_cb: StatusCallback = None,
) -> dict[str, list[dict]]:
    """Filter papers for quality and relevance. Returns filtered structured data."""
    cb = status_cb or _noop
    cb("Filtering papers...")

    minimal = {}
    for cat, papers in structured_data.items():
        minimal[cat] = [
            {"doi": p["doi"], "title": p["title"], "venue": p.get("venue", ""), "affiliation": ""}
            for p in papers
        ]

    result = complete(
        model=model, system=prompts.FILTER,
        user=json.dumps({"papers": minimal, "limit_filter": limit}, indent=2),
        response_format=FilterResult, api_key=api_key, base_url=base_url,
    )
    if isinstance(result, str):
        raise RuntimeError(f"Filter LLM returned invalid response. Raw: {result[:200]}")

    reasons: dict[str, str] = {}
    for cat_papers in result.papers.values():
        for p in cat_papers:
            reasons[p.doi] = p.reason

    filtered: dict[str, list[dict]] = {}
    for cat, papers in structured_data.items():
        kept = [{**p, "reason_for_inclusion": reasons[p["doi"]]} for p in papers if p["doi"] in reasons]
        if kept:
            filtered[cat] = kept

    cb(f"Selected {sum(len(v) for v in filtered.values())} papers after filtering.")
    return filtered


def run_report(
    filtered_data: dict[str, list[dict]],
    model: str,
    date_range: str = "N/A",
    api_key: str | None = None,
    base_url: str | None = None,
    status_cb: StatusCallback = None,
) -> str:
    """Generate Markdown report from filtered papers."""
    cb = status_cb or _noop
    cb("Generating report...")

    result = complete(
        model=model, system=prompts.REPORTER.replace("{date_range}", date_range),
        user=json.dumps(filtered_data, indent=2, ensure_ascii=False),
        api_key=api_key, base_url=base_url,
    )
    cb("Report generated.")
    return result


def _resolve_agent(agent_models: dict | None, agent_name: str,
                   fallback_model: str, fallback_key: str | None, fallback_url: str | None,
                   ) -> tuple[str, str | None, str | None]:
    """Resolve (model, api_key, base_url) for an agent from agent_models."""
    if agent_models and isinstance(agent_models, dict):
        am = agent_models.get(agent_name)
        if am and isinstance(am, dict):
            return (
                am.get("name") or fallback_model,
                am.get("api_key") or fallback_key,
                am.get("base_url") or fallback_url,
            )
    return fallback_model, fallback_key, fallback_url


def run_pipeline(
    query: str | None,
    model: str,
    db_path: str = "output",
    api_key: str | None = None,
    ss_api_key: str | None = None,
    base_url: str | None = None,
    agent_models: dict | None = None,
    limit_search: int = 100,
    limit_filter: int = 20,
    categories: list[str] | None = None,
    include_abstracts: bool = True,
    fields_of_study: list[str] | None = None,
    publication_date_or_year: str | None = None,
    skip_search: bool = False,
    use_updater_json: bool = False,
    use_filtered_json: bool = False,
    existing_json_path: str | None = None,
    merge_new_to_old: bool = False,
    status_cb: StatusCallback = None,
) -> tuple[dict, str]:
    """Run full pipeline with optional skip/resume controls.

    Returns (filtered_data, report_markdown).
    """
    from .db import Paper, get_session

    cb = status_cb or _noop
    os.makedirs(db_path, exist_ok=True)

    updater_path = existing_json_path or os.path.join(db_path, "updater.json")
    filtered_path = os.path.join(db_path, "updater_filter.json")

    # --- Fast path: reuse filtered results ---
    if use_filtered_json:
        cb("Skipping search + annotate + filter (use_filtered_json=true)")
        if not os.path.exists(filtered_path):
            raise FileNotFoundError(f"Not found: {filtered_path}")
        with open(filtered_path, "r", encoding="utf-8") as f:
            filtered = json.load(f)
        m, k, u = _resolve_agent(agent_models, "reporter", model, api_key, base_url)
        report = run_report(
            filtered_data=filtered, model=m,
            date_range=publication_date_or_year or "N/A",
            api_key=k, base_url=u, status_cb=cb,
        )
        return filtered, report

    # --- Skip annotate: reuse updater.json ---
    if use_updater_json:
        cb("Skipping search + annotate (use_updater_json=true)")
        if not os.path.exists(updater_path):
            raise FileNotFoundError(f"Not found: {updater_path}")
        with open(updater_path, "r", encoding="utf-8") as f:
            structured = json.load(f)
        m, k, u = _resolve_agent(agent_models, "filterer", model, api_key, base_url)
        filtered = run_filter(
            structured_data=structured, model=m, limit=limit_filter,
            api_key=k, base_url=u, status_cb=cb,
        )
        with open(filtered_path, "w", encoding="utf-8") as f:
            json.dump(filtered, f, indent=2, ensure_ascii=False)
        cb(f"Saved filtered data to {filtered_path}")
        m, k, u = _resolve_agent(agent_models, "reporter", model, api_key, base_url)
        report = run_report(
            filtered_data=filtered, model=m,
            date_range=publication_date_or_year or "N/A",
            api_key=k, base_url=u, status_cb=cb,
        )
        return filtered, report

    # --- Search phase ---
    if skip_search:
        cb("Skipping search (skip_search=true), loading from DB")
        session = get_session(db_path)
        db_papers = session.query(Paper).all()
        session.close()
        if not db_papers:
            raise RuntimeError("No papers in database. Run search first.")
        papers = [
            {"doi": p.doi, "title": p.title, "abstract": p.abstract, "venue": p.venue}
            for p in db_papers
        ]
    else:
        if not query:
            raise RuntimeError("query is required when skip_search is false")
        papers = run_search(
            query=query, db_path=db_path, api_key=ss_api_key, limit=limit_search,
            fields_of_study=fields_of_study, publication_date_or_year=publication_date_or_year,
            status_cb=cb,
        )
        if not papers:
            raise RuntimeError("No papers found for the given query. Try broadening your search terms.")

    # --- Annotate phase ---
    m, k, u = _resolve_agent(agent_models, "annotator", model, api_key, base_url)
    structured = run_annotate(
        papers=papers, model=m, categories=categories,
        include_abstracts=include_abstracts, api_key=k, base_url=u, status_cb=cb,
    )
    with open(updater_path, "w", encoding="utf-8") as f:
        json.dump(structured, f, indent=2, ensure_ascii=False)
    cb(f"Saved annotated data to {updater_path}")

    # --- Filter phase ---
    m, k, u = _resolve_agent(agent_models, "filterer", model, api_key, base_url)
    filtered = run_filter(
        structured_data=structured, model=m, limit=limit_filter,
        api_key=k, base_url=u, status_cb=cb,
    )
    with open(filtered_path, "w", encoding="utf-8") as f:
        json.dump(filtered, f, indent=2, ensure_ascii=False)
    cb(f"Saved filtered data to {filtered_path}")

    # --- Report phase ---
    m, k, u = _resolve_agent(agent_models, "reporter", model, api_key, base_url)
    report = run_report(
        filtered_data=filtered, model=m,
        date_range=publication_date_or_year or "N/A",
        api_key=k, base_url=u, status_cb=cb,
    )

    return filtered, report
