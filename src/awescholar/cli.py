"""CLI entry point for awescholar."""

import argparse
import json
import os
import re
import sys
from importlib.metadata import version, PackageNotFoundError

from dotenv import load_dotenv

from .pipeline import run_search, run_annotate, run_filter, run_report, run_pipeline
from .utils import merge_new_to_archive, merge_archive_to_new, update_readme, generate_rss


def get_version() -> str:
    try:
        return version("awescholar")
    except PackageNotFoundError:
        return "0.1.0"


def _expand_env_vars(value):
    """Replace ${VAR} patterns with environment variable values."""
    if isinstance(value, str):
        def _replace(m):
            return os.environ.get(m.group(1), "")
        return re.sub(r"\$\{(\w+)\}", _replace, value) or None
    if isinstance(value, list):
        return [_expand_env_vars(v) for v in value]
    if isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    return value


def load_config(path: str | None) -> dict:
    """Load config from JSON file, expanding ${ENV_VAR} patterns."""
    load_dotenv()
    config = {}
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            config = _expand_env_vars(json.load(f))

    return {
        "model": config.get("model") or os.getenv("AWESCHOLAR_MODEL", "gpt-4.1-mini"),
        "api_key": config.get("api_key") or os.getenv("AWESCHOLAR_API_KEY"),
        "base_url": config.get("base_url") or os.getenv("AWESCHOLAR_BASE_URL"),
        "ss_api_key": config.get("ss_api_key") or os.getenv("SEMANTICSCHOLAR_API_KEY"),
        "db_path": config.get("db_path") or os.getenv("AWESCHOLAR_DB_PATH", "output"),
        "limit_search": config.get("limit_search", 100),
        "limit_filter": config.get("limit_filter", 20),
        "categories": config.get("categories"),
        "fields_of_study": config.get("fields_of_study"),
        "publication_date": config.get("publication_date"),
        "include_abstracts": config.get("include_abstracts", True),
    }


def status(msg: str) -> None:
    print(f"  -> {msg}")


# ── Subcommands ──────────────────────────────────────────────

def cmd_search(args: argparse.Namespace, config: dict) -> int | None:
    papers = run_search(
        query=args.query,
        db_path=config["db_path"],
        api_key=config["ss_api_key"],
        limit=args.limit or config["limit_search"],
        fields_of_study=config["fields_of_study"],
        publication_date_or_year=args.date or config["publication_date"],
        status_cb=status,
    )
    print(f"\nSaved {len(papers)} papers to {config['db_path']}/papers.db")


def cmd_annotate(args: argparse.Namespace, config: dict) -> int | None:
    from .db import Paper, get_session

    session = get_session(config["db_path"])
    db_papers = session.query(Paper).all()
    session.close()

    if not db_papers:
        print("No papers in database. Run 'awescholar search <query>' first.")
        return 1

    papers = [
        {"doi": p.doi, "title": p.title, "abstract": p.abstract, "venue": p.venue}
        for p in db_papers
    ]

    structured = run_annotate(
        papers=papers, model=config["model"], categories=config["categories"],
        include_abstracts=config["include_abstracts"],
        api_key=config["api_key"], base_url=config["base_url"], status_cb=status,
    )

    out_path = os.path.join(config["db_path"], "updater.json")
    os.makedirs(config["db_path"], exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(structured, f, indent=2, ensure_ascii=False)
    print(f"\nSaved annotated data to {out_path}")


def cmd_filter(args: argparse.Namespace, config: dict) -> int | None:
    updater_path = os.path.join(config["db_path"], "updater.json")
    if not os.path.exists(updater_path):
        print(f"Not found: {updater_path}. Run 'awescholar annotate' first.")
        return 1

    with open(updater_path, "r", encoding="utf-8") as f:
        structured = json.load(f)

    filtered = run_filter(
        structured_data=structured, model=config["model"],
        limit=args.limit or config["limit_filter"],
        api_key=config["api_key"], base_url=config["base_url"], status_cb=status,
    )

    out_path = os.path.join(config["db_path"], "updater_filter.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(filtered, f, indent=2, ensure_ascii=False)
    print(f"\nSaved filtered data to {out_path}")


def cmd_report(args: argparse.Namespace, config: dict) -> int | None:
    filtered_path = os.path.join(config["db_path"], "updater_filter.json")
    if not os.path.exists(filtered_path):
        print(f"Not found: {filtered_path}. Run 'awescholar filter' first.")
        return 1

    with open(filtered_path, "r", encoding="utf-8") as f:
        filtered = json.load(f)

    report = run_report(
        filtered_data=filtered, model=config["model"],
        date_range=config.get("publication_date") or "N/A",
        api_key=config["api_key"], base_url=config["base_url"], status_cb=status,
    )

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\nReport saved to {args.output}")
    else:
        print("\n" + report)


def cmd_run(args: argparse.Namespace, config: dict) -> int | None:
    filtered, report = run_pipeline(
        query=args.query, model=config["model"], db_path=config["db_path"],
        api_key=config["api_key"], ss_api_key=config["ss_api_key"], base_url=config["base_url"],
        limit_search=args.limit_search or config["limit_search"],
        limit_filter=args.limit_filter or config["limit_filter"],
        categories=config["categories"], include_abstracts=config["include_abstracts"],
        fields_of_study=config["fields_of_study"],
        publication_date_or_year=args.date or config["publication_date"], status_cb=status,
    )

    output = args.output or os.path.join(config["db_path"], "report.md")
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport saved to {output}")


def cmd_update(args: argparse.Namespace, config: dict) -> int | None:
    new_path = args.input or os.path.join(config["db_path"], "updater_filter.json")
    if not os.path.exists(new_path):
        print(f"Not found: {new_path}. Run 'awescholar run' first.")
        return 1

    if args.direction == "new2old":
        merge_new_to_archive(new_path, args.archive)
        print(f"Merged new papers into {args.archive}")
    elif args.direction == "old2new":
        merge_archive_to_new(new_path, args.archive)
        print(f"Enriched {new_path} with archive papers")


def cmd_readme(args: argparse.Namespace, config: dict) -> int | None:
    readme_path = args.readme or os.path.join(os.path.dirname(args.archive), "readme.md")
    update_readme(
        archive_path=args.archive, readme_path=readme_path,
        project_title=args.title or "Awesome Scholar",
        project_description=args.description or "",
    )
    print(f"README updated at {readme_path}")


def cmd_rss(args: argparse.Namespace, config: dict) -> int | None:
    output = args.output or "rss.xml"
    generate_rss(archive_path=args.archive, output_path=output, title=args.title or "Awesome Scholar Updates")
    print(f"RSS feed generated at {output}")


# ── Main ─────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="awescholar",
        description="Automated scientific literature discovery and curation.",
    )
    parser.add_argument("-v", "--version", action="version", version=f"awescholar {get_version()}")
    parser.add_argument("--config", type=str, help="Path to config.json")
    sub = parser.add_subparsers(dest="command")

    # search
    p = sub.add_parser("search", help="Search Semantic Scholar for papers")
    p.add_argument("query", type=str, help="Search query string")
    p.add_argument("--limit", type=int, help="Max results (default: 100)")
    p.add_argument("--date", type=str, help="Date range, e.g. 2025-01-01:2025-05-30")

    # annotate
    sub.add_parser("annotate", help="Annotate papers with domain and category")

    # filter
    p = sub.add_parser("filter", help="Select top papers by quality and relevance")
    p.add_argument("--limit", type=int, help="Number of papers to keep (default: 20)")

    # report
    p = sub.add_parser("report", help="Generate Markdown report from filtered data")
    p.add_argument("-o", "--output", type=str, help="Output file path")

    # run
    p = sub.add_parser("run", help="Run full pipeline: search, annotate, filter, report")
    p.add_argument("query", type=str, help="Search query string")
    p.add_argument("--limit-search", type=int, help="Max search results (default: 100)")
    p.add_argument("--limit-filter", type=int, help="Papers to keep after filter (default: 20)")
    p.add_argument("--date", type=str, help="Date range, e.g. 2025-01-01:2025-05-30")
    p.add_argument("-o", "--output", type=str, help="Report output path")

    # update
    p = sub.add_parser("update", help="Merge data between new results and archive")
    p.add_argument("--direction", choices=["new2old", "old2new"], required=True)
    p.add_argument("--input", type=str, help="Path to new data JSON")
    p.add_argument("--archive", type=str, required=True, help="Path to archive JSON")

    # readme
    p = sub.add_parser("readme", help="Generate README tables from archive")
    p.add_argument("--archive", type=str, required=True, help="Path to archive JSON")
    p.add_argument("--readme", type=str, help="Output README path")
    p.add_argument("--title", type=str, help="Project title")
    p.add_argument("--description", type=str, help="Project description")

    # rss
    p = sub.add_parser("rss", help="Generate RSS feed from archive")
    p.add_argument("--archive", type=str, required=True, help="Path to archive JSON")
    p.add_argument("-o", "--output", type=str, help="Output RSS file path")
    p.add_argument("--title", type=str, help="Feed title")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    config = load_config(args.config)
    handlers = {
        "search": cmd_search, "annotate": cmd_annotate, "filter": cmd_filter,
        "report": cmd_report, "run": cmd_run, "update": cmd_update,
        "readme": cmd_readme, "rss": cmd_rss,
    }
    return handlers[args.command](args, config) or 0


if __name__ == "__main__":
    sys.exit(main())
