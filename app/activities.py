ACTIVITIES: list[dict[str, str]] = [
    {"value": "walking", "label": "Walking"},
    {"value": "running", "label": "Running"},
    {"value": "jumping", "label": "Jumping"},
    {"value": "cycling", "label": "Cycling"},
    {"value": "yoga", "label": "Yoga"},
    {"value": "jog", "label": "Jogging"},
    {"value": "stairs", "label": "Stairs"},
]

ACTIVITY_VALUES: set[str] = {a["value"] for a in ACTIVITIES}
