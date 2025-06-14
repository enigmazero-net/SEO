import string
from rake_nltk import Rake
from keybert import KeyBERT
from pytrends.request import TrendReq
import pandas as pd
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

def main():
    # 1) Prompt for text
    text = input("Please enter your text:\n")

    # 2) RAKE extraction: preserve ampersand in phrases
    punctuations = string.punctuation.replace("&", "")
    r = Rake(punctuations=punctuations)
    r.extract_keywords_from_text(text)
    all_phrases = r.get_ranked_phrases_with_scores()
    top5 = all_phrases[:5]
    alternatives = all_phrases[5:10]
    scores, phrases = zip(*top5)
    print("\nTop 5 RAKE keywords:", phrases)

    # 3) KeyBERT extraction for comparison
    kb = KeyBERT()
    kb_results = kb.extract_keywords(
        text,
        keyphrase_ngram_range=(1, 4),
        stop_words='english',
        top_n=5
    )
    print("\nTop 5 KeyBERT keywords:", [phrase for phrase, score in kb_results])

    # 4) Fetch Trends 2024–2025 for RAKE top5
    pytrends = TrendReq(hl="en-US", tz=0)
    pytrends.build_payload(phrases, timeframe="2024-01-01 2025-06-14")
    df = pytrends.interest_over_time().drop(columns=["isPartial"], errors="ignore")

    # 5) Attempt to fetch related queries
    try:
        related = pytrends.related_queries()
    except Exception:
        related = {}

    # 6) Fetch autocomplete suggestions per keyword
    suggestions = {}
    for kw in phrases:
        try:
            sugg = pytrends.suggestions(kw)
            suggestions[kw] = [item['title'] for item in sugg]
        except Exception:
            suggestions[kw] = []

    # 7) Resample to monthly mean
    df_monthly = df.resample("M").mean()
    df_monthly.index = df_monthly.index.to_period("M").strftime("%Y-%m")

    # 8) Transpose so rows = RAKE keywords
    df_t = df_monthly.T

    # 9) Write trends table
    table = df_t.reset_index().rename(columns={"index": "keyword"})
    table.insert(1, "RAKE_score", scores)
    with open("keyword_trends.txt", "w") as f:
        f.write(table.to_string(index=False))
    print("\nDone! Trends written to keyword_trends.txt")

    # 10) Write alternatives + KeyBERT + related/autocomplete suggestions
    with open("keyword_alternatives.txt", "w") as f:
        f.write("Alternative RAKE keywords (phrase + score):\n")
        for score, phrase in alternatives:
            f.write(f"- {phrase} (score: {score})\n")

        f.write("\nKeyBERT Keywords (phrase + score):\n")
        for phrase, score in kb_results:
            f.write(f"- {phrase} (score: {score:.4f})\n")

        f.write("\nRelated Queries (or autocomplete suggestions):\n")
        for kw in phrases:
            f.write(f"\nFor \"{kw}\":\n")
            info = related.get(kw)
            # Top related
            if info and info.get("top") is not None and not info["top"].empty:
                f.write("  Top related:\n")
                for val in info["top"]["query"].head(5):
                    f.write(f"    • {val}\n")
            else:
                f.write("  No top related. Using autocomplete suggestions:\n")
                for s in suggestions.get(kw, [])[:5]:
                    f.write(f"    • {s}\n")
            # Rising related
            if info and info.get("rising") is not None and not info["rising"].empty:
                f.write("  Rising related:\n")
                for val in info["rising"]["query"].head(5):
                    f.write(f"    • {val}\n")
            else:
                f.write("  No rising related.\n")
    print("\nDone! Alternatives and related suggestions written to keyword_alternatives.txt")

if __name__ == "__main__":
    main()
