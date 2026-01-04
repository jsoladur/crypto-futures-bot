import numpy as np

DEFAULT_SQLITE_BUSY_TIMEOUT = 30  # 30 seconds
TELEGRAM_REPLY_EXCEPTION_MESSAGE_MAX_LENGTH = 3_000
DEFAULT_CURRENCY_CODE = "USDT"
DEFAULT_FUTURES_EXCHANGE_TIMEOUT = 30_000  # 30 seconds
STABLE_COINS = [DEFAULT_CURRENCY_CODE, "USDC"]
DEFAULT_JOB_INTERVAL_SECONDS = 5  # 5 seconds
DEFAULT_IN_MEMORY_CACHE_TTL_IN_SECONDS = 86_400  # 1 day
DEFAULT_ATR_SL_MULT = 2.8
DEFAULT_ATR_TP_MULT = 3.5
# Event Emitter - Event names
SIGNALS_EVALUATION_RESULT_EVENT_NAME = "signals_evaluation_result"
TRIGGER_BUY_ACTION_EVENT_NAME = "trigger_buy_action"

RISK_MANAGEMENT_ALLOWED_VALUES_LIST = np.concatenate(
    (np.arange(0.25, 5.25, 0.25), np.arange(5.50, 10.50, 0.50), np.arange(11, 21, 1))
).tolist()

MEXC_WEB_API_BASE_URL = "https://futures.mexc.com/api"
MEXC_WEB_API_DEFAULT_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9,ru;q=0.8,it;q=0.7,la;q=0.6,vi;q=0.5,lb;q=0.4",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "dnt": "1",
    "language": "English",
    "origin": "https://www.mexc.com",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "referer": "https://www.mexc.com/",
    "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
    "x-language": "en-US",
}
MEXC_FUTURES_TAKER_FEES = 0.0004
DEFAULT_MARKET_SIGNAL_RETENTION_DAYS = 5

SL_MULTIPLIERS = [2.5, 2.8, 3.0, 3.2]
TP_MULTIPLIERS = [3.0, 3.5, 3.8, 4.0, 4.2, 4.5]

DEFAULT_LONG_ENTRY_OVERSOLD_THRESHOLD = 0.25
DEFAULT_SHORT_ENTRY_OVERBOUGHT_THRESHOLD = 0.75
LONG_ENTRY_OVERSOLD_THRESHOLDS = np.round(np.arange(0.05, 0.41, 0.05), 2).tolist()
SHORT_ENTRY_OVERBOUGHT_THRESHOLDS = np.round(np.arange(0.60, 0.96, 0.05), 2).tolist()


DEFAULT_RISK_MANAGEMENT_PERCENTAGE = 1.0
