from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "db.sqlite"


TORTOISE_ORM = {
    "connections": {
        "default": f"sqlite:///{DB_PATH}",
    },
    "apps": {
        "chores": {
            "models": ["src.chores_planner.models"],
            "migrations": "src.chores_planner.migrations",
            "default_connection": "default",
        }
    },
}
