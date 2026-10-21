"""Pick 50 Nexar train clips for the Wayve demo and write selection.csv."""

import csv
import random
from pathlib import Path

D = Path.home() / "demo_data/wayve/nexar"
# (split, light, weather filter, count)
BUCKETS = [
    ("positive", {"Dark"}, None, 12),
    ("negative", {"Dark"}, None, 8),
    ("positive", {"Twilight"}, None, 4),
    ("negative", {"Twilight"}, None, 2),
    ("positive", {"Normal"}, {"Rain"}, 4),
    ("negative", {"Normal"}, {"Rain"}, 4),
    ("positive", {"Normal"}, {"Clear", "Cloudy"}, 6),
    ("negative", {"Normal"}, {"Clear", "Cloudy"}, 10),
]

rng = random.Random(0)
rows = {s: list(csv.DictReader((D / f"meta_{s}.csv").open())) for s in ("positive", "negative")}
picked = []
for split, lights, weathers, n in BUCKETS:
    pool = [
        r
        for r in rows[split]
        if r["light_conditions"] in lights and (weathers is None or r["weather"] in weathers)
    ]
    for r in rng.sample(pool, n):
        picked.append({**r, "split": split, "near_miss": split == "positive"})
with (D / "selection.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(picked[0]))
    w.writeheader()
    w.writerows(picked)
print(len(picked), "clips")
