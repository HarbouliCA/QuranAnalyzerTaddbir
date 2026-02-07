import re

ARABIC_DIACRITICS = re.compile(r"[ًٌٍَُِّْـ]")

def normalize(text: str) -> str:
    text = ARABIC_DIACRITICS.sub("", text)
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ة", "ه")
    text = text.replace("ى", "ي")
    return text.strip()
