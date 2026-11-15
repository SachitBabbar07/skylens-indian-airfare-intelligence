"""Freeze the pre-Phase-3 state locally; never include private data in Git."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = ROOT / "backups" / f"phase3_{stamp}"
    dest.mkdir(parents=True)
    manifest = {}
    prefixes = ["src", "backend", "frontend/src", "scripts", "tests", "config",
                "docs", "reports", "models", "data/raw", "data/interim",
                "data/processed", "data/metadata"]
    files = set()
    for prefix in prefixes:
        files.update(p for p in (ROOT / prefix).rglob("*") if p.is_file()
                     and "__pycache__" not in p.parts and p.suffix != ".log")
    files.update(p for p in ROOT.iterdir() if p.is_file())
    with zipfile.ZipFile(dest / "working_implementation.zip", "x", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            name = path.relative_to(ROOT).as_posix()
            manifest[name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                              "bytes": path.stat().st_size}
            if not name.startswith(("data/raw/", "data/interim/", "data/processed/")):
                archive.write(path, name)
    (dest / "baseline_manifest.json").write_text(json.dumps({"files": manifest}, indent=2), encoding="utf-8")
    out = {"created_at_utc": stamp, "checkpoint_dir": dest.relative_to(ROOT).as_posix(),
           "file_count": len(manifest), "baseline_tests": 48,
           "archive_sha256": hashlib.sha256((dest / "working_implementation.zip").read_bytes()).hexdigest()}
    (ROOT / "data/metadata/phase3_checkpoint.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
