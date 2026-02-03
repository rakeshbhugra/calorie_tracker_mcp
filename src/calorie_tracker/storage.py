"""File-based storage for meals."""

import json
from datetime import datetime

from .config import MEALS_FILE, DATA_DIR


def ensure_data_dir() -> None:
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_meals() -> list[dict]:
    """Load meals from file."""
    if MEALS_FILE.exists():
        return json.loads(MEALS_FILE.read_text())
    return []


def save_meals(meals: list[dict]) -> None:
    """Save meals to file."""
    ensure_data_dir()
    MEALS_FILE.write_text(json.dumps(meals, indent=2))


def add_meal(food: str, calories: int) -> dict:
    """Add a new meal and return it."""
    meals = load_meals()
    meal = {
        "food": food,
        "calories": calories,
        "timestamp": datetime.now().isoformat()
    }
    meals.append(meal)
    save_meals(meals)
    return meal


def get_total_calories() -> int:
    """Get total calories for today."""
    meals = load_meals()
    return sum(m["calories"] for m in meals)


def clear_meals() -> None:
    """Clear all meals (for testing)."""
    save_meals([])
