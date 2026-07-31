import pandas as pd
from core.text_cleaner import TextCleaner

class TextAnalyzer:
    def __init__(self, cleaner: TextCleaner):
        self.cleaner = cleaner

    def extract_words(self, series: pd.Series) -> list[str]:
        return [
            word
            for text in series.dropna().astype(str)
            for word in self.cleaner.clean(text)
        ]

    def word_frequency(self, series: pd.Series) -> pd.DataFrame:
        words = self.extract_words(series)
        return (
        pd.Series(words)
        .value_counts()
        .rename_axis("palavra")
        .reset_index(name="frequencia")
    )