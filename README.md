# SEO Keyword Tools

This repository contains Python scripts for extracting keywords from text and for collecting search engine results.

## Requirements

- Python 3.10 or newer
- Firefox browser for Selenium
- The Python packages listed in `requirements.txt`

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

3. Download the NLTK datasets needed by RAKE:

   ```bash
   python download_nltk_data.py
   ```

## Usage

- **`demo_keywords.py`** prompts for a single text block, extracts keywords with RAKE and KeyBERT, and writes the results to text files.
- **`multi_keywords.py`** allows multiple texts and can optionally use YAKE and BERTopic for extra keywords, plus Selenium scraping of Google SERPs. The scraper waits 60 seconds after opening each results page so you can solve any CAPTCHA. Results are written to `keyword_alternatives_multi.txt` and `keyword_serp_multi.txt`.

Both scripts print instructions interactively when run.

### Optional Dependencies

- `yake` enables YAKE keyword extraction.
- `bertopic` and `umap-learn` enable topic modeling with BERTopic.

These packages are listed in `requirements.txt` but are not required for basic usage.


## License

This project is licensed under the [MIT License](LICENSE).

