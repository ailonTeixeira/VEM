#!/usr/bin/env python3
"""
Preview the exact prompt that will be sent to the LLM for a given commit.

Usage:
  python scripts/prompt_preview.py --index 0 --input mined_commits.csv --dir cloned_repos

  --index 0 Row index in the CSV to preview
  Optional:
  --diff-extensions .kt,.java  File extensions to include in diffs
  --prompt-file prompt.txt  Custom prompt template file
"""
import argparse
import csv
import itertools
import os
import sys
import pandas as pd
import git

# Ensure project root is on sys.path so `src` can be imported when running from other directories
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.classifier import LLMClassifier


def _resolve_repo_path(row, repos_dir):
    repo_url = str(row.get('repo_url', '') or '')
    repo_col = str(row.get('repo', '') or '')
    candidates = []
    if repo_url:
        candidates.append(repo_url.split('/')[-1].replace('.git', ''))
    if repo_col:
        candidates.append(repo_col)
    search_dirs = [repos_dir]
    if repos_dir and not repos_dir.endswith("_diff"):
        search_dirs.append(f"{repos_dir}_diff")

    for name in candidates:
        if not name:
            continue
        for base_dir in search_dirs:
            path = os.path.join(base_dir, name)
            if os.path.isdir(path):
                return path
    return None


def _get_raw_diff(repo_path, commit_sha):
    try:
        repo = git.Repo(repo_path)
        commit = repo.commit(commit_sha)
        if not commit.parents:
            return ""
        diff_text = ""
        for d in commit.diff(commit.parents[0], create_patch=True, max_count=5):
            diff_text += d.diff.decode('utf-8', errors='ignore') + "\n"
        return diff_text
    except Exception:
        return ""


def main():
    parser = argparse.ArgumentParser(description="Preview LLM prompt with commit_metadata, commit_message and commit_diff")
    parser.add_argument("--input", required=True, help="Path to mined_commits.csv")
    parser.add_argument("--dir", default="cloned_repos", help="Directory containing cloned repos")
    parser.add_argument("--index", type=int, default=0, help="Row index to preview")
    parser.add_argument("--diff-extensions", default=".kt", help="Comma-separated extensions to include in diff")
    parser.add_argument("--prompt-file", default=None, help="Optional prompt template file")
    parser.add_argument("--output", default=None, help="Write the prompt preview to a .txt file")
    parser.add_argument("--filter-diff-min", type=int, default=None, help="Filter and save commits with diff text length >= this value")
    parser.add_argument("--filter-diff-max", type=int, default=None, help="Filter and save commits with diff text length <= this value")
    parser.add_argument("--filter-output", default="filtered_commits.csv", help="Output file for filtered commits (used with --filter-diff-max)")
    args = parser.parse_args()

    df = None
    if args.filter_diff_max is None:
        df = pd.read_csv(args.input)
        if df.empty:
            raise SystemExit("Input CSV is empty")

    prompt_template = None
    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            prompt_template = f.read()

    classifier = LLMClassifier(
        input_csv=args.input,
        output_csv="/tmp/preview.csv",
        repos_dir=args.dir,
        prompt_template=prompt_template,
        diff_extensions=args.diff_extensions,
    )

    # --- Filtering Mode ---
    if args.filter_diff_max is not None or args.filter_diff_min is not None:
        lower_bound = args.filter_diff_min if args.filter_diff_min is not None else 0
        upper_bound = args.filter_diff_max if args.filter_diff_max is not None else float("inf")
        print(f"Filtering commits with diff length between {lower_bound} and {upper_bound}...")
        total = 0
        kept = 0
        reader = pd.read_csv(args.input, chunksize=1000)
        first_chunk = next(reader, None)
        if first_chunk is None or first_chunk.empty:
            raise SystemExit("Input CSV is empty")

        output_fields = list(first_chunk.columns) + [
            'metadata_length',
            'diff_text_length',
            'commit_message_length',
            'prompt_template_length',
            'total_context_length'
        ]

        with open(args.filter_output, "w", newline="", encoding="utf-8") as out_file:
            writer = csv.DictWriter(out_file, fieldnames=output_fields)
            writer.writeheader()

            for chunk in itertools.chain([first_chunk], reader):
                for _, r in chunk.iterrows():
                    total += 1
                    repo_path = _resolve_repo_path(r, args.dir)

                    msg, diff, metadata = "", "", ""
                    if repo_path:
                        details = classifier._get_commit_details(repo_path, r['commit_sha'])
                        # Prevenção caso uma versão antiga seja carregada
                        if details and len(details) == 3:
                            msg, diff, metadata = details
                        elif details and len(details) == 2:
                            msg, diff = details
                            metadata = "(no metadata)"
                        
                        raw_diff = _get_raw_diff(repo_path, r['commit_sha'])
                    else:
                        msg = r.get('commit_message', '') or r.get('message', '')
                        diff = ""
                        metadata = "(no metadata - repo not cloned)"
                        raw_diff = ""

                    commit_message = msg or ""
                    commit_diff = diff or ""
                    commit_metadata = metadata or "(no metadata)"
                    commit_diff_for_prompt = commit_diff if commit_diff else "(no diff)"

                    prompt = classifier.prompt_template.format(
                        commit_metadata=commit_metadata,
                        commit_message=commit_message,
                        commit_diff=commit_diff_for_prompt,
                    )

                    template_len = len(classifier.prompt_template.format(
                        commit_metadata="",
                        commit_message="",
                        commit_diff="",
                    ))
                    meta_len = len(commit_metadata)
                    diff_len = len(commit_diff_for_prompt)
                    message_len = len(commit_message)
                    context_len = template_len + message_len + diff_len + meta_len

                    if lower_bound <= diff_len <= upper_bound:
                        row_copy = r.to_dict()
                        row_copy['metadata_length'] = meta_len
                        row_copy['diff_text_length'] = diff_len
                        row_copy['commit_message_length'] = message_len
                        row_copy['prompt_template_length'] = template_len
                        row_copy['total_context_length'] = context_len
                        writer.writerow(row_copy)
                        kept += 1

        print(f"Done! Saved {kept} valid commits out of {total} to {args.filter_output}.")
        return

    # --- Standard Preview Mode ---
    if args.index < 0 or args.index >= len(df):
        raise SystemExit(f"Index out of range: {args.index} (0..{len(df)-1})")

    row = df.iloc[args.index]
    repo_name = str(row['repo_url']).split('/')[-1].replace('.git', '')
    repo_path = os.path.join(args.dir, repo_name)

    commit_message, commit_diff, commit_metadata = "", "", ""
    if os.path.exists(repo_path):
        details = classifier._get_commit_details(repo_path, row['commit_sha'])
        if details and len(details) == 3:
            commit_message, commit_diff, commit_metadata = details
        elif details and len(details) == 2:
            commit_message, commit_diff = details
            commit_metadata = "(no metadata)"
    else:
        commit_message = row.get('commit_message', '') or row.get('message', '')
        commit_diff = "(no diff - repo not cloned)"
        commit_metadata = "(no metadata - repo not cloned)"

    prompt = classifier.prompt_template.format(
        commit_metadata=commit_metadata or "(no metadata)",
        commit_message=commit_message or "",
        commit_diff=commit_diff or "(no diff)",
    )

    meta_len = len(commit_metadata) if commit_metadata else 0
    msg_len = len(commit_message) if commit_message else 0
    diff_len = len(commit_diff) if commit_diff else 0
    prompt_len = len(prompt)

    print("=== METADATA Length ===")
    print(f"{meta_len} characters")

    print("\n=== MESSAGE Length ===")
    print(f"{msg_len} characters")
    
    print("\n=== DIFF Length ===")
    print(f"{diff_len} characters")
    
    print("\n=== TOTAL CONTEXT Length (Sent to LLM) ===")
    print(f"{prompt_len} characters")

    print("\n-------------------------------------------")
    print("=== commit_metadata ===")
    print(commit_metadata or "(empty)")
    print("\n=== commit_message ===")
    print(commit_message or "(empty)")
    print("\n=== commit_diff ===")
    print(commit_diff or "(empty)")
    print("\n=== prompt ===")
    print(prompt)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(f"METADATA Length: {meta_len} chars\n")
            f.write(f"MESSAGE Length: {msg_len} chars\n")
            f.write(f"DIFF Length: {diff_len} chars\n")
            f.write(f"TOTAL CONTEXT Length: {prompt_len} chars\n")
            f.write("-------------------------------------------\n")
            f.write("=== commit_metadata ===\n")
            f.write((commit_metadata or "(empty)") + "\n\n")
            f.write("=== commit_message ===\n")
            f.write((commit_message or "(empty)") + "\n\n")
            f.write("=== commit_diff ===\n")
            f.write((commit_diff or "(empty)") + "\n\n")
            f.write("=== prompt ===\n")
            f.write(prompt + "\n")
        print(f"\nPrompt preview written to: {args.output}")


if __name__ == "__main__":
    main()
