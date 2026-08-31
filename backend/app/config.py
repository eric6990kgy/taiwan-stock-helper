import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_ROOT / 'investment_os.db'}")

# FinMind (Phase 5B). Registering for a free token raises the rate limit
# from 300/hr to 600/hr (Phase 5 Discovery Report Sec.4) -- optional, the
# adapter works unauthenticated too, just at the lower limit.
FINMIND_API_URL = os.getenv("FINMIND_API_URL", "https://api.finmindtrade.com/api/v4/data")
FINMIND_API_TOKEN = os.getenv("FINMIND_API_TOKEN")  # None is fine -- see above
