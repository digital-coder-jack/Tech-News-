import os
from pathlib import Path

env_path = Path(__file__).parent / ".env"

with open(env_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("DISCORD_TOKEN"):
            os.environ["DISCORD_TOKEN"] = line.strip().split("=", 1)[1]

print("DEBUG TOKEN:", os.getenv("DISCORD_TOKEN"))