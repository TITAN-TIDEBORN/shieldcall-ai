"""
ShieldCall AI — Configuration
All settings have sensible defaults. No .env file required for demo mode.
"""

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3"          # Options: "llama3", "mistral", "phi3", "gemma2"
OLLAMA_FALLBACK_MODE = True      # Use mock responses if Ollama is unavailable

RISK_THRESHOLD = 60              # Calls below this score are "forwarded"
AUTO_SIMULATE_INTERVAL = 0       # Seconds between auto-simulated calls (0 = off)

DATABASE_URL = "sqlite:///./shieldcall.db"

SUPPORTED_LANGUAGES = [
    "English", "Tamil", "Hindi", "Telugu", "Kannada",
    "Malayalam", "Bengali", "Marathi", "Gujarati",
    "Punjabi", "Odia", "Urdu"
]

# Official org prefixes that are typically landlines
OFFICIAL_NUMBER_PREFIXES = ["1800", "1860", "044", "011", "022", "040", "080", "0431"]

# Known scam keywords for detection
SCAM_KEYWORDS = [
    "rbi digital wallet", "trai disconnection", "kyc verification",
    "courier with drugs", "arrest warrant", "cbi officer", "income tax notice",
    "aadhaar deactivate", "uidai", "electricity cut", "customs clearance",
    "digital arrest", "money laundering", "drug parcel", "narcotics",
    "your account will be frozen", "press 1 to speak", "press 9",
    "stay on the line or you will be arrested"
]

URGENCY_KEYWORDS = [
    "immediately", "right now", "2 hours", "act now", "or else", "deadline",
    "last chance", "emergency", "final notice", "urgent", "abhi", "turant",
    "இப்போதே", "உடனே", "अभी", "तुरंत", "within minutes", "last warning",
    "account suspended", "disconnected today", "arrested"
]

OTP_KEYWORDS = [
    "otp", "one time password", "pin", "password", "cvv", "card number",
    "account number", "net banking", "upi pin", "mpin"
]

PAYMENT_KEYWORDS = [
    "pay now", "transfer", "upi", "gpay", "phonepe", "paytm", "wire",
    "send money", "abhi pay karo", "payment", "fine", "penalty",
    "clearance fee", "processing fee", "bail amount"
]
