import csv
import random
import uuid
from pathlib import Path


OUTPUT_FILE = Path("driving_log.csv")
ROW_COUNT = 200
SEED = 42


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def sample_trip(rng: random.Random, risk_profile: str) -> dict:
    if risk_profile == "safe":
        duration_minutes = clamp(rng.gauss(26, 9), 8, 85)
        avg_speed = clamp(rng.gauss(31, 5), 16, 48)
        distance_miles = clamp(duration_minutes * avg_speed / 60 + rng.uniform(-1.0, 1.5), 1.5, 55.0)
        hard_braking = rng.choices([0, 1, 2], weights=[0.68, 0.25, 0.07], k=1)[0]
        speeding = rng.choices([0, 1], weights=[0.8, 0.2], k=1)[0]
        night_ratio = rng.betavariate(1.2, 7.5)
        distraction = clamp(rng.gauss(0.18, 0.1), 0.0, 0.5)
    else:
        duration_minutes = clamp(rng.gauss(38, 14), 10, 110)
        avg_speed = clamp(rng.gauss(42, 8), 20, 72)
        distance_miles = clamp(duration_minutes * avg_speed / 60 + rng.uniform(-2.0, 3.0), 2.0, 90.0)
        hard_braking = rng.choices([1, 2, 3, 4, 5], weights=[0.12, 0.24, 0.28, 0.22, 0.14], k=1)[0]
        speeding = rng.choices([0, 1, 2, 3], weights=[0.08, 0.27, 0.37, 0.28], k=1)[0]
        night_ratio = rng.betavariate(2.8, 2.2)
        distraction = clamp(rng.gauss(0.68, 0.16), 0.25, 1.0)

    # Add mild cross-feature correlation so aggressive trips are not independent noise.
    if speeding >= 2:
        hard_braking = min(5, hard_braking + rng.choice([0, 1]))
        distraction = clamp(distraction + rng.uniform(0.03, 0.12), 0.0, 1.0)

    if hard_braking >= 4:
        distraction = clamp(distraction + rng.uniform(0.02, 0.08), 0.0, 1.0)

    night_driving_minutes = round(duration_minutes * night_ratio, 1)

    return {
        "trip_id": str(uuid.uuid4()),
        "duration_minutes": round(duration_minutes, 1),
        "distance_miles": round(distance_miles, 1),
        "hard_braking_events": hard_braking,
        "speeding_events": speeding,
        "night_driving_minutes": night_driving_minutes,
        "distraction_score": round(distraction, 2),
    }


def generate_dataset() -> list[dict]:
    rng = random.Random(SEED)
    rows = []

    for _ in range(ROW_COUNT):
        risk_profile = rng.choices(["safe", "high_risk"], weights=[0.62, 0.38], k=1)[0]
        rows.append(sample_trip(rng, risk_profile))

    return rows


def write_csv(rows: list[dict], output_file: Path) -> None:
    fieldnames = [
        "trip_id",
        "duration_minutes",
        "distance_miles",
        "hard_braking_events",
        "speeding_events",
        "night_driving_minutes",
        "distraction_score",
    ]

    with output_file.open("w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = generate_dataset()
    write_csv(rows, OUTPUT_FILE)
    print(f"Wrote {len(rows)} trips to {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
