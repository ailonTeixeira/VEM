#!/usr/bin/env python3
"""
Commands:
  mine      - run GitHub mining
  classify  - run LLM classification
  analyze   - run analysis on selected CSVs
"""
import argparse
import sys
from src.miner import GitHubMiner
from src.classifier import LLMClassifier
from src.analyzer import ClassificationAnalyzer


def cmd_mine(args):
    miner = GitHubMiner(args.token, args.query, args.max_repos, args.output, args.dir, None, print, max_commits_per_repo=args.per_repo)
    miner.mine()


def cmd_classify(args):
    classifier = LLMClassifier(
        args.input,
        args.output,
        args.dir,
        args.provider,
        args.model,
        args.host,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        prompt_template=args.prompt,
        log_callback=print,
        diff_extensions=args.diff_extensions,
    )
    classifier.classify()


def cmd_analyze(args):
    # args.csvs is a list of csv paths with optional model names: model:path or just path
    csv_list = []
    for item in args.csvs:
        if ":" in item:
            model, path = item.split(":", 1)
        else:
            # derive model name from filename
            import os
            base = os.path.basename(item)
            model = base.replace("commits_classification_", "").replace(".csv", "")
            path = item
        csv_list.append((model, path))
    analyzer = ClassificationAnalyzer(csv_list, print)
    plots = analyzer.analyze()
    # Save combined HTML locally
    from plotly.io import to_html
    html = "<html><head><script src='https://cdn.plot.ly/plotly-latest.min.js'></script></head><body>"
    for k, fig in plots.items():
        html += f"<h2>{k}</h2>"
        html += to_html(fig, full_html=False, include_plotlyjs=False)
    html += "</body></html>"
    out = args.output or "analysis_results.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Analysis written to {out}")


def main():
    p = argparse.ArgumentParser(prog="cbsoft")
    sub = p.add_subparsers(dest="cmd")

    pm = sub.add_parser("mine")
    pm.add_argument("--token", required=True)
    pm.add_argument("--query", default="language:kotlin topic:android stars:>500")
    pm.add_argument("--max-repos", type=int, default=100)
    pm.add_argument("--per-repo", type=int, default=None)
    pm.add_argument("--output", default="mined_commits.csv")
    pm.add_argument("--dir", default="cloned_repos")
    pm.set_defaults(func=cmd_mine)

    pc = sub.add_parser("classify")
    pc.add_argument("--input", required=True)
    pc.add_argument("--output", required=True)
    pc.add_argument("--dir", default="cloned_repos")
    pc.add_argument("--provider", default="ollama")
    pc.add_argument("--model", default="mistral")
    pc.add_argument("--host", default="http://localhost:11434/v1")
    pc.add_argument("--prompt", default=None)
    pc.add_argument("--temperature", type=float, default=0.2)
    pc.add_argument("--max-tokens", type=int, default=256)
    pc.add_argument("--diff-extensions", default=".kt", help="Comma-separated list of file extensions to include in diffs (e.g., .kt,.java)")
    pc.set_defaults(func=cmd_classify)

    pa = sub.add_parser("analyze")
    pa.add_argument("csvs", nargs='+', help="List of CSVs to analyze. Format: model:path or path")
    pa.add_argument("--output", help="HTML output file")
    pa.set_defaults(func=cmd_analyze)

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        sys.exit(1)
    args.func(args)

if __name__ == "__main__":
    main()
