# SEO Keyword Tools

This repository contains Python scripts for extracting keywords from text and for collecting search engine results.

## Requirements

- Python 3.10 or newer
- The Python packages listed in `requirements.txt`
- Playwright must download its browser binaries (see Setup)

Optional features require additional libraries as noted below.

## Setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Install Playwright browsers (only needed once):

   ```bash
   playwright install firefox
   ```

4. Download the NLTK datasets needed by RAKE:

   ```bash
   python download_nltk_data.py
   ```

## Usage

- **`demo_keywords.py`** prompts for a single text block, extracts keywords with RAKE and KeyBERT, and writes the results to text files.
- **`multi_keywords.py`** allows multiple texts and can optionally use YAKE and BERTopic for extra keywords, plus Playwright scraping of Google SERPs. After opening each results page it pauses until you press **Enter**, giving you time to solve any CAPTCHA. Results are written to `keyword_alternatives_multi.txt` and `keyword_serp_multi.txt`.

Both scripts print instructions interactively when run.

### Optional Dependencies

- `yake` enables YAKE keyword extraction.
- `bertopic` and `umap-learn` enable topic modeling with BERTopic.

These packages are optional and can be installed with:

```bash
pip install yake bertopic umap-learn
```

They are not required for basic usage.

