"""Check local Markdown links while allowing explicitly regenerable research figures."""
from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def main():
    missing = []
    checked = 0
    generated = 0
    paths = list(ROOT.glob("*.md")) + list((ROOT / "docs").glob("*.md")) + list((ROOT / "reports").glob("*.md"))
    for path in paths:
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            target = target.strip("<>").split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (path.parent / unquote(target)).resolve()
            if resolved.is_relative_to(ROOT / "reports/figures"):
                generated += 1
                continue
            checked += 1
            if not resolved.exists():
                missing.append(f"{path.relative_to(ROOT)}: {target}")
    for entry in missing:
        print(entry)
    print(f"Checked {checked} local links; {generated} regenerable figure links; missing={len(missing)}")
    raise SystemExit(bool(missing))


if __name__ == "__main__":
    main()
