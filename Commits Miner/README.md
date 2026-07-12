# Commits Mining and Classification Tool
This is a unified tool with a user-friendly graphical interface for automating the search, sorting, and analysis of commits in GitHub repositories. Designed for software engineering researchers, it allows you to collect raw commit data, sort them using large language models (LLMs), and analyze the sorting to generate insights.

## Features

- **Mining Tab**: Search and clone GitHub repositories based on language, topic, and star criteria. Scan commits for keywords related to code smells.
- **Classification Tab**: Classify mined commits using local LLMs via Ollama API.
- **Analysis Tab**: Analyze and compare classifications from multiple LLMs with interactive plots and matrices.
- **File Manager Tab**: Browse and select CSV files.

## Requirements

- Python 3.8+
- Git
- GitHub Token (for API access)
- Ollama (for local LLM inference)
- Dependencies listed in `requirements.txt`

## System Configuration for Local LLMs

The tool and LLMs have been tested and optimized for the following hardware configuration:
- **CPU**: Intel® Core™ i7-1165G7 (11th Gen) @ 2.80GHz × 8
- **RAM**: 24 GB
- **OS**: Ubuntu 22.04.5 LTS

### Recommended Local LLMs (Ollama)

For classification, the following models are recommended and available via the dropdown menu:
- `mistral`: Mistral 7B/8B (Instruct v0.3)
- `llama3`: Meta Llama 3 8B
- `codellama`: CodeLlama 7B
- `deepseek-coder`: DeepSeek-Coder 6.7B/7B

## Installation and Setup

### 1. Clone the Repository
```bash
git clone https://github.com/
cd CommitsMiner
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Ollama
Install Ollama from [ollama.ai](https://ollama.ai).

Pull the required models for classification:
```bash
ollama pull mistral
ollama pull llama3
ollama pull codellama
ollama pull deepseek-coder
```

Ensure Ollama is running:
```bash
ollama serve
```

### 4. Run the Tool
```bash
python3 main.py
```

## Usage

1. **Mining**:
   - Enter GitHub token, language (e.g., kotlin), topic (e.g., android), min stars.
   - Set max repos and optional max commits per repo.
   - Choose output CSV and repos directory.
   - Load or edit keywords JSON.
   - Click "Start Mining".

2. **Classification**:
   - Select input CSV, output CSV, repos dir.
   - Configure Ollama host and model.
   - Adjust **Temperature**, **Max Tokens**, and **Diff File Extensions** (comma-separated, e.g., `.kt,.java,.py`) to match the language you mined.
   - Edit prompt template if needed.
   - Click "Start Classification".

3. **Analysis**:
   - Select multiple classified CSV files from different LLMs.
   - Click "Analyze" to generate comparison plots and matrices.

4. **File**:

## Command-Line Interface (CLI)

This project provides a lightweight CLI (`cli.py`) so you can run mining, classification and analysis from within containers or on headless servers.

Examples:

- Run mining:
```bash
python3 cli.py mine --token $GITHUB_TOKEN --query "language:kotlin topic:android stars:>500" --max-repos 100 --per-repo 50 --output mined_commits.csv --dir cloned_repos
```

- Run classification (using Ollama):
```bash
python3 cli.py classify --input commits_candidates.csv --output classified_commits.csv --dir cloned_repos --provider ollama --model mistral --host http://localhost:11434/v1 --temperature 0.2 --max-tokens 256 --diff-extensions .kt
```

- Run analysis and write a single HTML file:
```bash
python3 cli.py analyze CodeLlama-7B:/path/to/commits_classification_codellama7b.csv Llama-3-8B:/path/to/commits_classification_llama.csv --output analysis.html
```

Recommended defaults for 8B-class models (e.g., Mistral 7B/8B):
- **Temperature**: 0.1
- **Max Tokens**: 256 (classification outputs are short, keep this low for speed)
- **Diff extensions**: `.kt` for Kotlin; set to `.java`, `.py`, `.js`, etc. when analyzing other languages.

## Prompt Preview Test

Preview the exact prompt that will be sent to the LLM for a given commit.

- **Usage**:
```bash
  python3 scripts/prompt_preview.py --index 0 --input mined_commits.csv --dir cloned_repos
  ```

  `--index 0`                Row index in the CSV to preview
- **Optional**: 
  `--diff-extensions .kt,.java`  File extensions to include in diffs
  `--prompt-file prompt.txt`  Custom prompt template file

## Performance Notes

- **Average Execution Time**: < 12 hours for LLMs < 9B parameters analyzing 500 commits.
- **Memory Usage**: ~8 GB RAM per LLM.
- **Tested Hardware**:
  - CPU: Intel® Core™ i7-1165G7 (11th Gen) @ 2.80GHz × 8
  - RAM: 24 GB
  - OS: Ubuntu 22.04.5 LTS

## Architecture

- `gui.py`: Main GUI application with tabs.
- `src/miner.py`: GitHub repository mining and commit scanning.
- `src/classifier.py`: LLM-based commit classification.
- `src/analyzer.py`: Analysis and plotting of classification results.


## cloned_repos
https://drive.google.com/drive/folders/16hDUt99LhSKbs1KJbTkCLn8_bMvz3lRf?usp=sharing
## commits_candidates
https://drive.google.com/file/d/1G0Ib8XCaLzyLzk47RN7ZnO_dZvYErqi_/view?usp=sharing

## License

MIT License
