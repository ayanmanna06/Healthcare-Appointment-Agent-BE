import os
from functools import lru_cache

PROMPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "prompts"))

@lru_cache(maxsize=32)
def load_prompt(filename: str) -> str:
    """
    Reads a prompt template from the project's prompts/ directory (.txt file).
    """
    if not filename.endswith(".txt"):
        filename = f"{filename}.txt"
    file_path = os.path.join(PROMPTS_DIR, filename)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()
