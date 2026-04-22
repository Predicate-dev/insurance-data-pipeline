import csv
import random
import uuid
from dataclasses import dataclass
from pathlib import Path


COLUMNS = [
    "trip_id",
    "duration_minutes",
    "distance_miles",
    "hard_braking_events",
    "speeding_events",
    "night_driving_minutes",
    "distraction_score",
]


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


@dataclass(frozen=True)
class Profile:
    slug: str
    title: str
    safe_weight: float  # 0..1
    night_beta_a: float
    night_beta_b: float
    distraction_shift: float
    speeding_shift: float
    braking_shift: float


PROFILES: list[Profile] = [
    Profile(
        slug="sample_1_low_risk_commuter.csv",
        title="Low Risk Commuter",
        safe_weight=0.88,
        night_beta_a=1.1,
        night_beta_b=10.0,
        distraction_shift=-0.05,
        speeding_shift=-0.2,
        braking_shift=-0.2,
    ),
    Profile(
        slug="sample_2_medium_risk_mixed.csv",
        title="Medium Risk Mixed Driver",
        safe_weight=0.62,
        night_beta_a=1.7,
        night_beta_b=5.8,
        distraction_shift=0.00,
        speeding_shift=0.0,
        braking_shift=0.0,
    ),
    Profile(
        slug="sample_3_high_risk_aggressive.csv",
        title="High Risk Aggressive Driver",
        safe_weight=0.22,
        night_beta_a=2.6,
        night_beta_b=2.4,
        distraction_shift=0.12,
        speeding_shift=0.4,
        braking_shift=0.35,
    ),
    Profile(
        slug="sample_4_night_owl.csv",
        title="Night Owl (High Exposure)",
        safe_weight=0.55,
        night_beta_a=4.0,
        night_beta_b=1.6,
        distraction_shift=0.05,
        speeding_shift=0.10,
        braking_shift=0.05,
    ),
    Profile(
        slug="sample_5_distracted_driver.csv",
        title="Distracted Driver",
        safe_weight=0.58,
        night_beta_a=1.8,
        night_beta_b=5.5,
        distraction_shift=0.22,
        speeding_shift=0.05,
        braking_shift=0.05,
    ),
]


def _sample_base_trip(rng: random.Random, kind: str) -> tuple[float, float, int, int, float]:
    """
    Returns (duration_minutes, avg_speed_mph, hard_braking_events, speeding_events, distraction_score)
    """
    if kind == "safe":
        duration_minutes = clamp(rng.gauss(24, 8), 8, 85)
        avg_speed = clamp(rng.gauss(30, 5), 16, 48)
        hard_braking = rng.choices([0, 1, 2], weights=[0.70, 0.23, 0.07], k=1)[0]
        speeding = rng.choices([0, 1], weights=[0.82, 0.18], k=1)[0]
        distraction = clamp(rng.gauss(0.16, 0.10), 0.0, 0.55)
    else:
        duration_minutes = clamp(rng.gauss(40, 14), 10, 110)
        avg_speed = clamp(rng.gauss(44, 8), 20, 72)
        hard_braking = rng.choices([1, 2, 3, 4, 5], weights=[0.10, 0.22, 0.30, 0.24, 0.14], k=1)[0]
        speeding = rng.choices([0, 1, 2, 3], weights=[0.08, 0.26, 0.38, 0.28], k=1)[0]
        distraction = clamp(rng.gauss(0.66, 0.16), 0.20, 1.0)

    return duration_minutes, avg_speed, hard_braking, speeding, distraction


def sample_trip(rng: random.Random, profile: Profile) -> dict:
    kind = rng.choices(["safe", "high_risk"], weights=[profile.safe_weight, 1.0 - profile.safe_weight], k=1)[0]
    duration_minutes, avg_speed, hard_braking, speeding, distraction = _sample_base_trip(rng, kind)

    # Apply profile tweaks (kept simple and deterministic).
    distraction = clamp(distraction + profile.distraction_shift + rng.uniform(-0.03, 0.03), 0.0, 1.0)

    speeding_f = clamp(speeding + profile.speeding_shift + rng.uniform(-0.35, 0.35), 0.0, 3.0)
    speeding = int(round(speeding_f))

    braking_f = clamp(hard_braking + profile.braking_shift + rng.uniform(-0.35, 0.35), 0.0, 5.0)
    hard_braking = int(round(braking_f))

    # Add mild correlations: more speeding often pairs with harsher braking and higher distraction.
    if speeding >= 2:
        hard_braking = min(5, hard_braking + rng.choice([0, 1]))
        distraction = clamp(distraction + rng.uniform(0.03, 0.10), 0.0, 1.0)

    # Night driving minutes based on beta ratio (bounded).
    night_ratio = rng.betavariate(profile.night_beta_a, profile.night_beta_b)
    night_minutes = round(duration_minutes * night_ratio, 1)

    distance_miles = clamp(duration_minutes * avg_speed / 60 + rng.uniform(-1.5, 2.0), 1.0, 95.0)

    return {
        "trip_id": str(uuid.uuid4()),
        "duration_minutes": round(duration_minutes, 1),
        "distance_miles": round(distance_miles, 1),
        "hard_braking_events": int(clamp(hard_braking, 0, 5)),
        "speeding_events": int(clamp(speeding, 0, 3)),
        "night_driving_minutes": night_minutes,
        "distraction_score": round(distraction, 2),
    }


def generate_csv(output_path: Path, profile: Profile, *, rows: int, seed: int) -> None:
    rng = random.Random(seed)
    data = [sample_trip(rng, profile) for _ in range(rows)]

    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(data)


def main() -> None:
    base_seed = 2026
    rows = 200

    for i, profile in enumerate(PROFILES):
        out = Path(profile.slug)
        generate_csv(out, profile, rows=rows, seed=base_seed + i * 97)
        print(f"Wrote {rows} rows -> {out} ({profile.title})")


if __name__ == "__main__":
    main()

