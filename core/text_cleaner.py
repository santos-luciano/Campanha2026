import re
from unidecode import unidecode
from nltk.corpus import stopwords

class TextCleaner:
    def __init__(self, language="portuguese", min_len=3):
        self.stopwords = set(stopwords.words(language))
        self.min_len = min_len

    def clean(self, text: str) -> list[str]:
        text = text.lower()
        text = unidecode(text)
        text = re.sub(r"[^a-z0-9\s]", " ", text)
#        text = re.sub(r"[^a-z\s]", " ", text)
        return [
            word
            for word in text.split()
            if word not in self.stopwords and len(word) >= self.min_len
        ]