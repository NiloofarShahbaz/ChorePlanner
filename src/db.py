from src import DB_PATH


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
