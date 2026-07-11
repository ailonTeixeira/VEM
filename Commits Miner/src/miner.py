import os
import sys
import pandas as pd
from github import Github, RateLimitExceededException, GithubException
import git
import time
import logging
import json
import shutil
import csv
import threading

class GitHubMiner:
    def __init__(self, token, query, max_repos=100, output_csv='mined_commits.csv', repos_dir='cloned_repos', keywords=None, log_callback=None, max_commits_per_repo=None):
        self.token = token
        self.query = query
        self.max_repos = max_repos
        self.output_csv = output_csv
        self.repos_dir = repos_dir
        self.keywords = keywords or self._default_keywords()
        self.log_callback = log_callback or print
        self.max_commits_per_repo = max_commits_per_repo
        self.running = True

    def stop(self):
        self.running = False
        self.log_callback("Stop requested by user.")

    def _default_keywords(self):
        return {
            "EnergySmell": ["battery", "power", "energy", "wakelock", "drain", "sleep", "performance", "optimization", "efficient"],
            "ConcurrencySmell": ["race condition", "deadlock", "thread safety", "concurrency", "synchronize", "atomic", "volatile", "coroutine bug", "thread-safe"],
            "StorageBloatSmell": ["apk size", "storage", "bloat", "compress", "webp", "shrink", "proguard", "asset"],
            "SecurityVulnerability": ["security", "vulnerability", "cve-", "xss", "injection", "rce", "exploit", "harden", "sanitize"],
            "HighComplexityDebt": ["refactor", "cleanup", "simplify", "readability", "maintainability", "spaghetti", "tech debt", "refactoring"]
        }

    def mine(self):
        self.running = True
        if not self.token:
            raise ValueError("GitHub token is required")
        os.makedirs(self.repos_dir, exist_ok=True)
        g = Github(self.token)
        repo_urls = self._search_repos(g)
        if not repo_urls:
            self.log_callback("No repositories found")
            return
        total_written = 0
        for i, repo_url in enumerate(repo_urls):
            if not self.running:
                self.log_callback("Mining stopped by user.")
                break
            self.log_callback(f"Processing repo {i+1}/{len(repo_urls)}: {repo_url}")
            if i > 0 and i % 20 == 0:
                self.log_callback("Sleeping 10 seconds to reduce rate limiting...")
                time.sleep(10)
            local_path = self._clone_or_pull(repo_url)
            if not self.running:
                self.log_callback("Mining stopped by user.")
                break
            if local_path:
                commits = self._scan_commits(local_path)
                if not self.running:
                    self.log_callback("Mining stopped by user.")
                    break
                if commits:
                    self._write_csv(commits, append=(i > 0))
                    total_written += len(commits)
        if self.running:
            self.log_callback(f"Mining complete. Total commits: {total_written}")
        else:
            self.log_callback(f"Mining stopped. {total_written} commits saved in '{self.output_csv}'.")

    def _search_repos(self, github_client):
        self.log_callback(f"Searching GitHub: {self.query}")
        repo_urls = []
        try:
            repos = github_client.search_repositories(query=self.query)
            for i, repo in enumerate(repos):
                if i >= self.max_repos:
                    break
                repo_urls.append(repo.clone_url)
        except Exception as e:
            self.log_callback(f"Search failed: {e}")
        return repo_urls

    def _clone_or_pull(self, repo_url):
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        local_path = os.path.join(self.repos_dir, repo_name)
        if os.path.exists(local_path):
            try:
                repo = git.Repo(local_path)
                repo.remotes.origin.pull()
            except Exception as e:
                self.log_callback(f"Pull failed: {e}")
                shutil.rmtree(local_path)
                git.Repo.clone_from(repo_url, local_path)
        else:
            git.Repo.clone_from(repo_url, local_path)
        return local_path

    def _scan_commits(self, repo_path):
        found_commits = []
        seen = set()
        count = 0
        try:
            repo = git.Repo(repo_path)
            for commit in repo.iter_commits():
                if not self.running:
                    break
                if self.max_commits_per_repo and count >= self.max_commits_per_repo:
                    break
                msg = (commit.message or "").lower()
                for category, words in self.keywords.items():
                    for word in words:
                        if word.lower() in msg:
                            key = (repo.remotes.origin.url, commit.hexsha)
                            if key not in seen:
                                seen.add(key)
                                found_commits.append({
                                    "repo_url": repo.remotes.origin.url,
                                    "commit_sha": commit.hexsha,
                                    "commit_message": commit.message.strip(),
                                    "potential_category": category,
                                    "matched_word": word
                                })
                                count += 1
                            break
                    else:
                        continue
                    break
        except Exception as e:
            self.log_callback(f"Scan failed for {repo_path}: {e}")
        return found_commits

    def _write_csv(self, commits, append=False):
        mode = 'a' if append and os.path.exists(self.output_csv) else 'w'
        write_header = mode == 'w'
        with open(self.output_csv, mode, newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["repo_url", "commit_sha", "commit_message", "potential_category", "matched_word"])
            if write_header:
                writer.writeheader()
            writer.writerows(commits)
