"""Keep factual source summaries in Git; retain individual examples locally only.

Run after source acquisition/report generation and before staging the registry.
Original local file_profiles/checkpoint artifacts preserve source inspection.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT / "data/metadata/dataset_registry.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    removed = 0

    def clean(obj):
        nonlocal removed
        if isinstance(obj, dict):
            if "sample" in obj:
                del obj["sample"]
                removed += 1
            for child in obj.values():
                clean(child)
        elif isinstance(obj, list):
            for child in obj:
                clean(child)

    clean(value)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"Removed {removed} individual source-example fields; schema/hash/license summaries retained.")


if __name__ == "__main__":
    main()
