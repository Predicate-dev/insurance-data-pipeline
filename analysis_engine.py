import csv
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_CSV_PATH = Path("driving_log.csv")


@dataclass
class DriverAggregateStats:
    trip_count: int
    avg_duration_minutes: float
    avg_distance_miles: float
    avg_hard_braking_events: float
    avg_speeding_events: float
    avg_night_driving_minutes: float
    avg_distraction_score: float
    total_hard_braking_events: int
    total_speeding_events: int
    total_night_driving_minutes: float
    personalized_risk_score: float


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def load_trip_rows(csv_path: Path | str = DEFAULT_CSV_PATH) -> list[dict[str, str]]:
    path = Path(csv_path)
    with path.open(newline="") as csvfile:
        return list(csv.DictReader(csvfile))


def calculate_personalized_risk_score(
    avg_hard_braking_events: float,
    avg_speeding_events: float,
    avg_distraction_score: float,
) -> float:
    """
    Score each driver's typical trip behavior using the provided weighted formula.

    We intentionally use per-trip averages instead of raw totals so the score remains
    on a useful 0-100 scale even when a driver has many trips in the CSV.
    """
    penalty = (
        (avg_hard_braking_events * 5)
        + (avg_speeding_events * 10)
        + (avg_distraction_score * 20)
    )
    return round(clamp(100 - penalty, 0, 100), 1)


def summarize_driver(csv_path: Path | str = DEFAULT_CSV_PATH) -> DriverAggregateStats:
    rows = load_trip_rows(csv_path)
    if not rows:
        raise ValueError("driving_log.csv is empty.")

    trip_count = len(rows)
    total_duration_minutes = sum(float(row["duration_minutes"]) for row in rows)
    total_distance_miles = sum(float(row["distance_miles"]) for row in rows)
    total_hard_braking = sum(int(row["hard_braking_events"]) for row in rows)
    total_speeding = sum(int(row["speeding_events"]) for row in rows)
    total_night_minutes = sum(float(row["night_driving_minutes"]) for row in rows)
    total_distraction = sum(float(row["distraction_score"]) for row in rows)

    avg_hard_braking = total_hard_braking / trip_count
    avg_speeding = total_speeding / trip_count
    avg_distraction = total_distraction / trip_count
    score = calculate_personalized_risk_score(
        avg_hard_braking_events=avg_hard_braking,
        avg_speeding_events=avg_speeding,
        avg_distraction_score=avg_distraction,
    )

    return DriverAggregateStats(
        trip_count=trip_count,
        avg_duration_minutes=round(total_duration_minutes / trip_count, 1),
        avg_distance_miles=round(total_distance_miles / trip_count, 1),
        avg_hard_braking_events=round(avg_hard_braking, 2),
        avg_speeding_events=round(avg_speeding, 2),
        avg_night_driving_minutes=round(total_night_minutes / trip_count, 1),
        avg_distraction_score=round(avg_distraction, 2),
        total_hard_braking_events=total_hard_braking,
        total_speeding_events=total_speeding,
        total_night_driving_minutes=round(total_night_minutes, 1),
        personalized_risk_score=score,
    )


def get_llm_risk_coaching(
    stats: DriverAggregateStats,
    model: str = "gpt-4o",
    api_key: str | None = None,
) -> dict[str, Any]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError(
            "The OpenAI Python SDK is required. Install it with `pip install openai`."
        ) from exc

    if not api_key and not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError(
            "Provide api_key or set the OPENAI_API_KEY environment variable before calling the API."
        )

    client = OpenAI(api_key=api_key) if api_key else OpenAI()
    stats_payload = json.dumps(asdict(stats), indent=2)

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a telematics safety coach. Review the aggregate driving stats and "
                    "return JSON only. Keep coaching_advice friendly, specific, and action-oriented."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Analyze these aggregate driving stats and return the driver's risk summary.\n"
                    f"{stats_payload}"
                ),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "driver_risk_summary",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "risk_category": {
                            "type": "string",
                            "enum": ["Low", "Medium", "High"],
                        },
                        "top_risk_factor": {
                            "type": "string",
                        },
                        "coaching_advice": {
                            "type": "string",
                        },
                    },
                    "required": [
                        "risk_category",
                        "top_risk_factor",
                        "coaching_advice",
                    ],
                    "additionalProperties": False,
                },
            }
        },
    )

    if getattr(response, "status", None) != "completed":
        raise RuntimeError(f"OpenAI response did not complete successfully: {response.status}")

    output_text = getattr(response, "output_text", None)
    if not output_text:
        raise RuntimeError("OpenAI response missing output_text.")

    payload = json.loads(output_text)
    return {
        "risk_category": payload["risk_category"],
        "top_risk_factor": payload["top_risk_factor"],
        "coaching_advice": payload["coaching_advice"],
    }


def analyze_driver(csv_path: Path | str = DEFAULT_CSV_PATH, model: str = "gpt-4o") -> dict[str, Any]:
    stats = summarize_driver(csv_path)
    llm_summary = get_llm_risk_coaching(stats, model=model)
    return {
        "stats": asdict(stats),
        "llm_summary": llm_summary,
    }


def main() -> None:
    stats = summarize_driver(DEFAULT_CSV_PATH)
    print("Aggregate stats:")
    print(json.dumps(asdict(stats), indent=2))

    if os.getenv("OPENAI_API_KEY"):
        print("\nLLM summary:")
        print(json.dumps(get_llm_risk_coaching(stats), indent=2))
    else:
        print("\nSkipping LLM call because OPENAI_API_KEY is not set.")


if __name__ == "__main__":
    main()
