"""Stage 4a: join features + labels, then split by TIME (past = train, future = test)."""
import pandas as pd

features = pd.read_csv("features.csv", parse_dates=["created_at"])
labels = pd.read_csv("labels.csv")

# inner join: keeps only labelled rows (drops the warm-up week). CHECK the count, never trust it silently.
data = features.merge(labels, on="event_id", how="inner")
assert len(data) == len(labels), f"lost rows in the join: {len(data)} vs {len(labels)}"
print("labelled rows:", len(data))

# split by time: first 5 days = train, last 2 days = test
CUTOFF = pd.Timestamp("2026-11-06", tz="UTC")
train = data[data["created_at"] < CUTOFF]
test = data[data["created_at"] >= CUTOFF]

print(f"train: {len(train)} rows, {train['is_attack'].sum()} attacks")
print(f"test:  {len(test)} rows, {test['is_attack'].sum()} attacks")
print("\nattack kinds per side:")
print(pd.crosstab(data["kind"], data["created_at"] >= CUTOFF).rename(columns={False: "train", True: "test"}))
