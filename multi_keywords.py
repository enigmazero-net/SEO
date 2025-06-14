import string
import csv
from rake_nltk import Rake
from keybert import KeyBERT
from umap import UMAP
import asyncio
from playwright.async_api import async_playwright
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

async def scrape_google_serp(url, num_results=5):

    results = []
    async with async_playwright() as p:
        # Launch Firefox in non-headless mode so the window is visible
        browser = await p.firefox.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)
        input("Press Enter when the page is fully loaded...")

        # For debugging: Save current HTML
        html = await page.content()
        with open("last_serp.html", "w", encoding="utf-8") as f:
            f.write(html)

        # Each organic result block is in a div.tF2Cxc
        result_divs = await page.query_selector_all("div.tF2Cxc")
        for div in result_divs[:num_results]:
            try:
                # Title
                title_el = await div.query_selector("h3")
                # Link (always inside .yuRUbf > a)
                link_el = await div.query_selector(".yuRUbf > a")
                # Snippet (try both main snippet classes)
                snippet_el = await div.query_selector("div.VwiC3b, div.IsZvec")
                results.append({
                    "title": await title_el.inner_text() if title_el else "",
                    "link": await link_el.get_attribute("href") if link_el else "",
                    "snippet": await snippet_el.inner_text() if snippet_el else "",
                })
            except Exception:
                # For debugging, you may want to print(e)
                continue
        await browser.close()

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

    # With RAKE, KeyBERT and YAKE all enabled in a single pass, running the
    # pipeline once provides plenty of keywords.  Multiple runs are no longer
    # necessary, so we fix the loop to a single iteration.
    num_runs = 1
    print("Running the pipeline once...")

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

            # Combine and deduplicate keywords across methods
            all_kw = []
            for score, kw in top5:
                all_kw.append(("RAKE", kw, score))
            for score, kw in alternatives:
                all_kw.append(("RAKE_alt", kw, score))
            for kw, score in kb_results:
                all_kw.append(("KeyBERT", kw, score))
            for kw, score in yake_results:
                all_kw.append(("YAKE", kw, score))
            for kw, score in topic_keywords:
                all_kw.append(("BERTopic", kw, score))

            unique_kw = []
            seen_kw = set()
            for method, kw, score in all_kw:
                key = kw.lower()
                if key not in seen_kw:
                    seen_kw.add(key)
                    unique_kw.append((method, kw, score))

            # Log to CSV using unique keywords
            for method, kw, score in unique_kw:
                csv_writer.writerow([run, method, kw, score])

            # Write unified keyword list per run
            alt_f.write(f"=== Run {run} ===\n")
            alt_f.write("Unique keywords from all extractors (method + score):\n")
            for method, kw, score in unique_kw:
                alt_f.write(f"- {kw} [{method}] (score: {score})\n")
            alt_f.write("\n" + "="*50 + "\n")

            # Human-in-the-loop scraping: prompt for each keyword
            serp_f.write(f"=== Run {run} ===\n")
            # Use the combined list of unique keywords from all extraction
            # methods so Google searches cover RAKE, YAKE, KeyBERT and
            # BERTopic results.  This helps diversify the search terms and
            # reduces repetition across runs.
            for _, kw, _ in unique_kw:
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
                    serp_data = asyncio.run(scrape_google_serp(url))
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
