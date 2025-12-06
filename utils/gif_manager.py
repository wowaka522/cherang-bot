import os
import random

BASE = "assets/cherrang"

GROUPS = {
    "neutral": "neutral",
    "happy": "happy",
    "angry": "angry",
    "shy": "shy",
    "sad": "sad",
}

def get_random_cat_gif(emotion: str = "neutral"):
    folder = GROUPS.get(emotion, "neutral")
    full_path = os.path.join(BASE, folder)

    if not os.path.exists(full_path):
        return None

    files = [f for f in os.listdir(full_path) if f.endswith(".gif")]
    if not files:
        return None

    return os.path.join(full_path, random.choice(files))