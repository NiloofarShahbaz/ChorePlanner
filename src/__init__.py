from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "db.sqlite"
_CREDENTIALS_DIR = DATA_DIR / "credentials"
TOKEN_PATH = _CREDENTIALS_DIR / "token.json"
CREDENTIALS_PATH = _CREDENTIALS_DIR / "credentials.json"