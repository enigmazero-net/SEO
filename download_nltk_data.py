import nltk

# download the tokenizers and stopword lists that rake-nltk needs
nltk.download("punkt")       # standard sentence tokenizer
nltk.download("punkt_tab")   # the “table” variant RAKE expects
nltk.download("stopwords")   # for ignoring common words
print("NLTK data downloaded!")
