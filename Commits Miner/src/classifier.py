import os
import subprocess
import sys
import logging
import pandas as pd
import git
import openai
import json
import re
import requests
from typing import Tuple

class LLMClassifier:
    def __init__(self, input_csv, output_csv, repos_dir, provider='ollama', model='deepseek-coder:6.7b', host='http://localhost:11440', temperature=0.1, max_tokens=256, prompt_template=None, log_callback=None, diff_extensions=None, diff_trunc=400000, api_key=None):
        self.input_csv = input_csv
        self.output_csv = output_csv
        self.repos_dir = repos_dir
        self.provider = provider
        self.model = model
        self.host = host
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.prompt_template = prompt_template or self._default_prompt()
        self.log_callback = log_callback or print
        self.diff_extensions = self._normalize_extensions(diff_extensions)
        self.diff_trunc = int(diff_trunc or 400000)
        self.api_key = api_key
        self.running = True

    def stop(self):
        self.running = False
        self.log_callback("Stop requested by user.")

    def _normalize_extensions(self, diff_extensions):
        if diff_extensions is None:
            return ['.kt']
        if isinstance(diff_extensions, str):
            raw = [x.strip() for x in diff_extensions.split(',') if x.strip()]
        else:
            raw = [str(x).strip() for x in diff_extensions if str(x).strip()]
        normalized = []
        for ext in raw:
            if not ext.startswith('.'):
                ext = '.' + ext
            normalized.append(ext.lower())
        return normalized or ['.kt']

    def _default_prompt(self):
        return """
CONTEXT AND PERSONA
You are an automated static code analyst. Your expertise is identifying and classifying code smells in commits, focusing on the Kotlin ecosystem for Android. Your analysis should be technical, meticulous, and based exclusively on the metadata, message and changes (diff) provided.

TASK
Analyze the following COMMIT DATA by following these steps:
1. REVIEW the commit metadata (stats and files changed) to grasp the scope of the change.
2. INTERPRET the commit message to understand the developer's stated intent.
3. EXAMINE the code diff line by line to validate the actual changes.
4. CLASSIFY whether the changes correspond to fixing code smells from CODE SMELL CATEGORIES or NONE.
5. JUSTIFY your decision based on the evidence found in the diff and metadata.

COMMIT DATA
[METADATA]:
{commit_metadata}

[MESSAGE]:
{commit_message}

[DIFF]:
{commit_diff}

CODE SMELL CATEGORIES
Use ONLY these categories for your classification:
EnergySmell: Optimizations related to battery/CPU consumption (e.g., improper wakelock management, unnecessary polling, blocking operations in the main thread, inefficient coroutines).
ConcurrencySmell: Concurrency and thread-safety issues (e.g., race conditions, deadlocks, incorrect use of coroutine scopes/dispatchers, access to shared state without synchronization).
StorageBloatSmell: Storage optimizations (disk/APK) (e.g., removing redundant assets or resources, optimizing image size, clearing the cache, reducing disk writes).
SecurityVulnerability: Security vulnerability fixes (e.g., (exposure of sensitive data, lack of input sanitization, use of insecure APIs, or excessive permissions).
HighComplexityDebt: Refactoring to reduce technical debt and improve code structure (e.g., removing long methods, eliminating duplicate code, simplifying complex conditions, improving variable names).

OUTPUT FORMAT (STRICT)
Return ONLY a single valid JSON object. No markdown blocks, no code fences, no conversational text.
The JSON must contain exactly these two keys:

   "classification": "EnergySmell" | "ConcurrencySmell" | "StorageBloatSmell" | "SecurityVulnerability" | "HighComplexityDebt" | "None",
   "reason": "A short technical justification grounded in the diff evidence (1-4 sentences)."
   """

    def classify(self):
        self.running = True
        client = None
        self._use_ollama = False
        self._use_gemini = False
        
        if self.provider == 'ollama':
            self._use_ollama = True
        elif self.provider == 'openai':
            api_key = self.api_key or os.environ.get('OPENAI_API_KEY')
            if not api_key:
                raise ValueError('OPENAI_API_KEY not set for provider=openai')
            openai.api_key = api_key
            client = openai
        else:
            if self.provider == 'gemini':
                self._use_gemini = True
            else:
                self._use_ollama = True

        df_candidates = pd.read_csv(self.input_csv)
        self.log_callback(f"Processing {len(df_candidates)} candidate commits with model {self.model}.")

        if os.path.exists(self.output_csv):
            df_results = pd.read_csv(self.output_csv)
            processed_shas = set(df_results['commit_sha'])
            self.log_callback(f"Resuming from {len(processed_shas)} processed commits.")
        else:
            df_results = pd.DataFrame()
            processed_shas = set()

        commits_to_process = df_candidates[~df_candidates['commit_sha'].isin(processed_shas)].reset_index(drop=True)
        self.log_callback(f"{len(commits_to_process)} new commits to process.")

        new_results_batch = []
        for index, row in commits_to_process.iterrows():
            if not self.running:
                self.log_callback("Classification stopped by user.")
                break
            commit_sha = row['commit_sha']
            self.log_callback(f"Processing commit {commit_sha} ({index + 1}/{len(commits_to_process)})")
            repo_name = row['repo_url'].split('/')[-1].replace('.git', '')
            repo_path = os.path.join(self.repos_dir, repo_name)
            
            if not os.path.exists(repo_path):
                self.log_callback(f"Repo directory not found: {repo_path}. Falling back to CSV commit message.")
                message = row.get('commit_message', '') or row.get('message', '')
                if pd.isna(message) or not message:
                    self.log_callback(f"No commit message available for {commit_sha}; skipping.")
                    continue
                diff = "(no diff - repo not cloned)"
                metadata = "(no metadata - repo not cloned)"
            else:
                message, diff, metadata = self._get_commit_details(repo_path, commit_sha)
                if message is None:
                    continue

            if not self.running:
                self.log_callback("Classification stopped by user.")
                break

            classification, reason = self._classify_commit(message, diff or '', metadata or '', client)

            if not self.running:
                self.log_callback("Classification stopped by user.")
                break

            result_row = row.to_dict()
            result_row['llm_model'] = self.model
            result_row['llm_classification'] = classification
            result_row['llm_reason'] = reason
            new_results_batch.append(result_row)
            self.log_callback(f"Model classification: {classification}")

            if len(new_results_batch) >= 10:  # Batch save
                temp_df = pd.DataFrame(new_results_batch)
                df_results = pd.concat([df_results, temp_df], ignore_index=True)
                df_results.to_csv(self.output_csv, index=False, encoding='utf-8')
                new_results_batch = []
                self.log_callback(f"Progress saved! {len(df_results)} commits in output file.")

        if new_results_batch:
            temp_df = pd.DataFrame(new_results_batch)
            df_results = pd.concat([df_results, temp_df], ignore_index=True)
            df_results.to_csv(self.output_csv, index=False, encoding='utf-8')

        if self.running:
            self.log_callback(f"Process completed! {len(df_results)} commits classified in '{self.output_csv}'.")
        else:
            self.log_callback(f"Classification stopped. {len(df_results)} commits saved in '{self.output_csv}'.")

    def _get_commit_details(self, repo_path, commit_sha):
        try:
            repo = git.Repo(repo_path)
            commit = repo.commit(commit_sha)
            
            # --- NOVO: Extração de Metadados Ricos ---
            stats = commit.stats.total
            files_changed_list = list(commit.stats.files.keys())
            
            metadata = (
                f"Author Date: {commit.authored_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Total Files Changed: {stats['files']}\n"
                f"Lines Inserted: {stats['insertions']}\n"
                f"Lines Deleted: {stats['deletions']}\n"
                f"Impacted Files: {', '.join(files_changed_list[:20])}" + ("..." if len(files_changed_list) > 20 else "")
            )
            # ----------------------------------------

            if not commit.parents:
                return commit.message, "(First commit, no diff)", metadata

            diff_text = ""
            # Removido o 'max_count=5' para não perder alterações espalhadas por múltiplos arquivos
            for d in commit.diff(commit.parents[0], create_patch=True):
                if d.a_path:
                    path = d.a_path.lower()
                    if any(path.endswith(ext) for ext in self.diff_extensions):
                        diff_text += d.diff.decode('utf-8', errors='ignore') + "\n"
                        
            if len(diff_text) > self.diff_trunc:
                diff_text = diff_text[:self.diff_trunc] + "\n... (diff truncated due to token limits.)"
                
            if diff_text:
                return commit.message, diff_text, metadata
                
            return commit.message, f"(No matching files changed in diff for extensions: {', '.join(self.diff_extensions)}) Classify this commit as None and justify this reason", metadata
            
        except Exception as e:
            self.log_callback(f"Error getting commit details {commit_sha} in {repo_path}: {e}")
            return None, None, None

    def _ollama_request(self, model, messages, temperature, max_tokens):
        url = self.host.rstrip('/')
        if '/v1' in url:
            endpoint = url if url.endswith('/chat/completions') else url + '/chat/completions'
            is_native = False
        else:
            endpoint = url + '/api/generate'
            is_native = True
            
        headers = {'Content-Type': 'application/json'}
        
        if is_native:
            full_prompt = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
            payload = {
                'model': model,
                'prompt': full_prompt,
                'stream': False,
                'format': 'json',
                'options': {
                    'temperature': temperature,
                    'num_predict': max_tokens
                }
            }
        else:
            payload = {
                'model': model,
                'messages': messages,
                'temperature': temperature,
                'max_tokens': max_tokens,
            }
            
        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=600)
            if resp.status_code == 404 and is_native:
                endpoint = url + '/api/chat'
                payload = {
                    'model': model,
                    'messages': messages,
                    'stream': False,
                    'options': {'temperature': temperature}
                }
                resp = requests.post(endpoint, json=payload, headers=headers, timeout=600)

            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if self.running:
                self.log_callback(f"Ollama Request Failed ({endpoint}): {e}")
            raise e

    def _classify_commit(self, commit_message: str, commit_diff: str, commit_metadata: str, client) -> Tuple[str, str]:
        if not self.running:
            return None, None

        # Adicionado o commit_metadata na formatação do prompt
        prompt = self.prompt_template.format(
            commit_metadata=commit_metadata or "(no metadata)",
            commit_message=commit_message or "", 
            commit_diff=commit_diff or "(no diff)"
        )

        try:
            if getattr(self, '_use_ollama', False):
                resp = self._ollama_request(self.model, [{"role": "user", "content": prompt}], self.temperature, self.max_tokens)
            else:
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
        except Exception as e:
            if self.running:
                self.log_callback(f'API request error: {e}')
            return 'api_error', str(e)

        content = None
        try:
            if isinstance(resp, dict):
                choices = resp.get('choices')
                if choices and len(choices) > 0:
                    ch = choices[0]
                    if isinstance(ch.get('message'), dict):
                        content = ch['message'].get('content')
                    else:
                        content = ch.get('text') or ch.get('content')
                elif 'response' in resp:
                    content = resp['response']
                elif 'message' in resp and isinstance(resp['message'], dict):
                    content = resp['message'].get('content')
                else:
                    content = json.dumps(resp)
            else:
                if hasattr(resp, 'choices') and resp.choices:
                    ch = resp.choices[0]
                    if hasattr(ch, 'message') and ch.message:
                        content = ch.message.get('content') if isinstance(ch.message, dict) else ch.message.content
                    else:
                        content = getattr(ch, 'text', None)
                else:
                    content = getattr(resp, 'text', None) or (json.dumps(resp) if not isinstance(resp, str) else resp)
        except Exception as e:
            self.log_callback(f'Error extracting content from response: {e}')
            return 'api_error', str(e)

        if not content:
            return 'api_error', 'No text content returned by model'

        try:
            parsed = json.loads(content)
        except Exception:
            m = re.search(r"\{[\s\S]*\}", content)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                except Exception as e:
                    self.log_callback(f'Failed to parse JSON: {e}')
                    return 'parse_error', content[:1000]
            else:
                return 'parse_error', content[:1000]

        valid_categories = {
            'energysmell': 'EnergySmell',
            'concurrencysmell': 'ConcurrencySmell',
            'storagebloatsmell': 'StorageBloatSmell',
            'securityvulnerability': 'SecurityVulnerability',
            'highcomplexitydebt': 'HighComplexityDebt',
            'none': 'None'
        }
        
        classification = None
        if isinstance(parsed, dict):
            for key in ['classification', 'label', 'category', 'class']:
                val = parsed.get(key)
                if val and isinstance(val, str):
                    clean_val = val.replace(' ', '').lower()
                    if clean_val in valid_categories:
                        classification = valid_categories[clean_val]
                        break
            
            if not classification:
                for val in parsed.values():
                    if isinstance(val, str):
                        clean_val = val.replace(' ', '').lower()
                        if clean_val in valid_categories:
                            classification = valid_categories[clean_val]
                            break
        
        if not classification:
            self.log_callback(f"Warning: Could not extract valid category from JSON. Content was: {content[:200]}")
            classification = 'unknown'

        return str(classification), parsed.get('reason', '') if isinstance(parsed, dict) else ''
