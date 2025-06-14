import string
import csv
from rake_nltk import Rake
from keybert import KeyBERT
from umap import UMAP
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.service import Service
import time
import warnings

# Optional keyword extraction libraries
try:
    import yake
except Exception:
    yake = None  # YAKE not installed

try:
    from bertopic import BERTopic
except Exception:
    BERTopic = None  # BERTopic not installed

warnings.filterwarnings("ignore", category=FutureWarning)

def scrape_google_serp(url, num_results=5, wait=60):

    options = Options()
    driver = None
    results = []
    try:
        driver = webdriver.Firefox(
            service=Service(GeckoDriverManager().install()), options=options
        )
        driver.set_page_load_timeout(max(wait, 30))
        driver.get(url)
        print(f"Waiting {wait} seconds for the page to load. Solve any CAPTCHA if present...")
        time.sleep(wait)

        # For debugging: Save current HTML
        with open("last_serp.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        # Each organic result block is in a div.tF2Cxc
        result_divs = driver.find_elements(By.CSS_SELECTOR, "div.tF2Cxc")
        for div in result_divs[:num_results]:
            try:
                # Title
                title_el = div.find_element(By.CSS_SELECTOR, "h3")
                # Link (always inside .yuRUbf > a)
                link_el = div.find_element(By.CSS_SELECTOR, ".yuRUbf > a")
                # Snippet (try both main snippet classes)
                try:
                    snippet_el = div.find_element(By.CSS_SELECTOR, "div.VwiC3b")
                except Exception:
                    try:
                        snippet_el = div.find_element(By.CSS_SELECTOR, "div.IsZvec")
                    except Exception:
                        snippet_el = None
                results.append({
                    "title": title_el.text,
                    "link": link_el.get_attribute("href"),
                    "snippet": snippet_el.text if snippet_el else "",
                })
            except Exception:
                # For debugging, you may want to print(e)
                continue
    finally:
        if driver is not None:
            driver.quit()

    return results


def main():
    # Collect texts for keyword extraction
    while True:
        try:
            num_prompts = int(input("How many texts would you like to enter?: ").strip())
            if num_prompts > 0:
                break
            else:
                print("Please enter a positive number.")
        except ValueError:
            print("Please enter a valid integer.")

    texts = []
    for i in range(num_prompts):
        txt = input(f"Text #{i+1}: ").strip()
        while not txt:
            txt = input(f"Text #{i+1} (cannot be empty): ").strip()
        texts.append(txt)
    combined_text = " ".join(texts)

    try:
        num_runs = int(input("How many times to run the pipeline? (default 1): ").strip() or 1)
    except ValueError:
        num_runs = 1

    with open("keyword_alternatives_multi.txt", "w") as alt_f, \
         open("keyword_serp_multi.txt", "w", encoding="utf-8") as serp_f, \
         open("keyword_log.csv", "w", newline="", encoding="utf-8") as csv_f:
        csv_writer = csv.writer(csv_f)
        csv_writer.writerow(["run", "method", "keyword", "score"])

        for run in range(1, num_runs + 1):
            print(f"\n=== Run {run}/{num_runs} ===")

            # RAKE extraction
            punctuations = string.punctuation.replace("&", "")
            r = Rake(punctuations=punctuations)
            r.extract_keywords_from_text(combined_text)
            all_phrases = r.get_ranked_phrases_with_scores()
            seen = set()
            deduped_phrases = []
            for score, phrase in all_phrases:
                p_clean = phrase.strip().lower()
                if p_clean not in seen:
                    deduped_phrases.append((score, phrase))
                    seen.add(p_clean)
            top5 = deduped_phrases[:5]
            alternatives = deduped_phrases[5:10]
            if top5:
                scores, phrases = zip(*top5)
                print("Top 5 RAKE keywords:", phrases)
            else:
                phrases = []

            # KeyBERT extraction
            kb = KeyBERT()
            kb_results = kb.extract_keywords(
                combined_text,
                keyphrase_ngram_range=(1, 4),
                stop_words="english",
                top_n=5,
            )
            print("Top 5 KeyBERT keywords:", [phrase for phrase, _ in kb_results])

            # YAKE extraction (if available)
            if yake is not None:
                kw_extractor = yake.KeywordExtractor(lan="en", n=3, top=5)
                yake_results = kw_extractor.extract_keywords(combined_text)
                print("Top 5 YAKE keywords:", [kw for kw, _ in yake_results])
            else:
                yake_results = []
                print("YAKE not installed; skipping YAKE extraction.")

            # BERTopic extraction (if available)
            if BERTopic is not None:
                if len(texts) >= 10:
                    num_docs = len(texts)
                    umap_model = UMAP(
                        n_neighbors=min(15, num_docs - 1),
                        n_components=min(2, num_docs - 1),
                    )
                    topic_model = BERTopic(verbose=False, umap_model=umap_model)
                    topics, _ = topic_model.fit_transform(texts)
                    topic_keywords = topic_model.get_topic(0) or []
                    topic_keywords = topic_keywords[:5]
                    print(
                        "Top 5 BERTopic keywords:",
                        [kw for kw, _ in topic_keywords],
                    )
                else:
                    topic_keywords = []
                    print(
                        "BERTopic requires at least 10 texts; skipping BERTopic extraction.",
                    )
            else:
                topic_keywords = []
                print("BERTopic not installed; skipping BERTopic extraction.")

            # Log to CSV
            for score, kw in top5:
                csv_writer.writerow([run, "RAKE", kw, score])
            for kw, score in kb_results:
                csv_writer.writerow([run, "KeyBERT", kw, score])
            for kw, score in yake_results:
                csv_writer.writerow([run, "YAKE", kw, score])
            for kw, score in topic_keywords:
                csv_writer.writerow([run, "BERTopic", kw, score])

            # Write alternatives + KeyBERT per run
            alt_f.write(f"=== Run {run} ===\n")
            alt_f.write("Top 5 RAKE keywords (phrase + score):\n")
            for score, phrase in top5:
                alt_f.write(f"- {phrase} (score: {score})\n")
            alt_f.write("\nAlternative RAKE keywords (phrase + score):\n")
            for score, phrase in alternatives:
                alt_f.write(f"- {phrase} (score: {score})\n")
            alt_f.write("\nTop 5 KeyBERT keywords (phrase + score):\n")
            for phrase, score in kb_results:
                alt_f.write(f"- {phrase} (score: {score:.4f})\n")
            if yake_results:
                alt_f.write("\nTop 5 YAKE keywords (phrase + score):\n")
                for phrase, score in yake_results:
                    alt_f.write(f"- {phrase} (score: {score})\n")
            if topic_keywords:
                alt_f.write("\nTop 5 BERTopic keywords (phrase + score):\n")
                for phrase, score in topic_keywords:
                    alt_f.write(f"- {phrase} (score: {score})\n")
            alt_f.write("\n" + "="*50 + "\n")

            # Human-in-the-loop scraping: prompt for each keyword
            serp_f.write(f"=== Run {run} ===\n")
            for kw in list(phrases):
                print(f"\n[!] Search for this keyword in Google: '{kw}'")
                print("    1. Open your browser, search this keyword on Google.")
                print("    2. Copy the URL of the results page.")
                url = input("    3. Paste the Google search results URL here (or press Enter to skip): ").strip()
                if not url:
                    print("    [Skipped!]")
                    serp_f.write(f"Keyword: {kw}\n    [Skipped]\n" + "="*50 + "\n")
                    continue
                print("    Opening browser and waiting for your action...")

                try:
                    serp_data = scrape_google_serp(url)
                except Exception as e:
                    print(f"  Error scraping SERP: {e}")
                    serp_f.write(f"Keyword: {kw}\n  Error scraping SERP for {url}: {e}\n" + "="*50 + "\n")
                    continue
                serp_f.write(f"Keyword: {kw}\n")
                if not serp_data:
                    serp_f.write(f"  No SERP results found for {url}.\n")
                for res in serp_data:
                    serp_f.write(f"- {res['title']}\n  {res['snippet']}\n  {res['link']}\n")
                serp_f.write("\n" + "="*50 + "\n")
                print("    Done! Results saved.")

    print("All keywords complete. SERP results written to keyword_serp_multi.txt")

if __name__ == "__main__":
    main()
