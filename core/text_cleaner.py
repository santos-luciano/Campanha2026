import re
from unidecode import unidecode
from nltk.corpus import stopwords

class TextCleaner:
    def __init__(self, language="portuguese", min_len=3):
        self.stopwords = set(stopwords.words(language))
        self.min_len = min_len
        # cobre a maioria dos blocos de emoji + símbolos pictográficos
        self._emoji_pattern = re.compile(
            "["
            "\U0001F300-\U0001FAFF"  # símbolos, pictogramas, emoticons, transporte etc.
            "\U00002600-\U000027BF"  # símbolos diversos + dingbats (inclui ♥ ☀ ✈ etc.)
            "\U0001F1E6-\U0001F1FF"  # bandeiras (regional indicators)
            "\U00002700-\U000027BF"
            "]+",
            flags=re.UNICODE,
        )

    def clean(self, text: str) -> list[str]:
        text = text.lower()
        text = self._emoji_pattern.sub(" ", text)   # remove emojis ANTES do unidecode
        text = unidecode(text)
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        return [
            word
            for word in text.split()
            if word not in self.stopwords and len(word) >= self.min_len
        ]