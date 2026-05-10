"""
Language detection service — uses keyword heuristics (no paid API).
"""

LANGUAGE_KEYWORDS = {
    "Tamil": ["நான்", "என்", "இல்லை", "ஆம்", "நன்றி", "வணக்கம்", "உங்கள்", "இப்போது", "இல்ல", "என்னோட"],
    "Hindi": ["नमस्ते", "मैं", "आप", "है", "हूँ", "धन्यवाद", "ठीक", "बात", "कहना", "जी", "हाँ", "नहीं", "कल", "अभी"],
    "Telugu": ["నమస్కారం", "నేను", "మీరు", "అవును", "కాదు", "ధన్యవాదాలు", "వెళ్ళండి"],
    "Kannada": ["ನಮಸ್ಕಾರ", "ನಾನು", "ನೀವು", "ಆಗದು", "ಧನ್ಯವಾದ", "ಸರಿ"],
    "Malayalam": ["നമസ്കാരം", "ഞാൻ", "നിങ്ങൾ", "ശരി", "ഇല്ല", "ആണ്", "ഏത്"],
    "Bengali": ["আমি", "আপনি", "ধন্যবাদ", "হ্যাঁ", "না", "ঠিক আছে", "নমস্কার"],
    "Marathi": ["नमस्कार", "मी", "तुम्ही", "आहे", "नाही", "ठीक आहे", "धन्यवाद"],
    "Gujarati": ["નમસ્તે", "હું", "આપ", "છે", "નહીં", "ધન્યવાદ", "ઠીક"],
    "Punjabi": ["ਸਤ ਸ੍ਰੀ ਅਕਾਲ", "ਮੈਂ", "ਤੁਸੀਂ", "ਹਾਂ", "ਨਹੀਂ", "ਧੰਨਵਾਦ"],
    "Odia": ["ନମସ୍କାର", "ମୁଁ", "ଆପଣ", "ହଁ", "ନା", "ଧନ୍ୟବାଦ"],
    "Urdu": ["السلام علیکم", "میں", "آپ", "ہاں", "نہیں", "شکریہ", "ٹھیک"],
}

LATIN_HINDI_KEYWORDS = ["namaste", "main", "aap", "hai", "hoon", "shukriya", "theek", "abhi", "turant", "baat", "karo", "karna"]
LATIN_TAMIL_KEYWORDS = ["vanakkam", "naan", "ungal", "illai", "aam", "nandri", "ippo", "enna", "sollunga"]


def detect_language(text: str) -> str:
    """
    Detect language from text using Unicode character ranges and keywords.
    Returns language name string. Defaults to 'English'.
    """
    if not text:
        return "English"

    text_lower = text.lower()

    # Check Unicode script keywords
    for lang, keywords in LANGUAGE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return lang

    # Latin-script Romanized Indian languages
    for kw in LATIN_HINDI_KEYWORDS:
        if kw in text_lower:
            return "Hindi"

    for kw in LATIN_TAMIL_KEYWORDS:
        if kw in text_lower:
            return "Tamil"

    # Check for Devanagari range (Hindi/Marathi)
    if any("\u0900" <= ch <= "\u097F" for ch in text):
        return "Hindi"

    # Check for Tamil range
    if any("\u0B80" <= ch <= "\u0BFF" for ch in text):
        return "Tamil"

    # Check for Telugu range
    if any("\u0C00" <= ch <= "\u0C7F" for ch in text):
        return "Telugu"

    # Check for Kannada range
    if any("\u0C80" <= ch <= "\u0CFF" for ch in text):
        return "Kannada"

    # Check for Malayalam range
    if any("\u0D00" <= ch <= "\u0D7F" for ch in text):
        return "Malayalam"

    # Check for Bengali range
    if any("\u0980" <= ch <= "\u09FF" for ch in text):
        return "Bengali"

    # Check for Gujarati range
    if any("\u0A80" <= ch <= "\u0AFF" for ch in text):
        return "Gujarati"

    # Check for Gurmukhi (Punjabi) range
    if any("\u0A00" <= ch <= "\u0A7F" for ch in text):
        return "Punjabi"

    # Check for Odia range
    if any("\u0B00" <= ch <= "\u0B7F" for ch in text):
        return "Odia"

    # Check for Arabic script (Urdu)
    if any("\u0600" <= ch <= "\u06FF" for ch in text):
        return "Urdu"

    return "English"
