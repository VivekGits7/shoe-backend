DEVICES: list[dict[str, str]] = [
    {"value": "shoe", "label": "Shoe"},
    {"value": "sandal", "label": "Sandal"},
]

DEVICE_VALUES: set[str] = {d["value"] for d in DEVICES}
