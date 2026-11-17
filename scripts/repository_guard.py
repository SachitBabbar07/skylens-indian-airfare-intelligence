"""Fail closed on secrets, private payloads and large Git blobs; print no matched values.

This focused local scanner supplements human review. It is not a proof that no
secret exists. Run --staged before every commit and --history before every push.
"""
import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 5 * 1024 * 1024
PATTERNS = {
    "private key": rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "GitHub token": rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{35,})\b",
    "AWS access key": rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "provider token": rb"\b(?:gsk_[A-Za-z0-9_-]{32,}|sk-[A-Za-z0-9_-]{32,}|AIza[A-Za-z0-9_-]{30,})\b",
    "URL credentials": rb"https?://[^\s/:]+:[^\s/@]+@",
    "assigned credential": rb'''(?i)(?:api_key|access_token|password|client_secret)\s*[=:]\s*["'][A-Za-z0-9+/=_-]{20,}["']''',
}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def inspect(name, content):
    problems = []
    p = Path(name)
    if (p.name.startswith(".env") and p.name != ".env.example") or p.suffix in {".pem", ".key", ".pfx", ".p12", ".cbm", ".parquet", ".zip", ".xlsx"}:
        problems.append("forbidden payload")
    if name.startswith(("data/raw/", "data/interim/", "data/processed/", "data/quotes/", "data/cache/", "backups/", ".tools/")):
        problems.append("private or regenerable payload")
    if len(content) > LIMIT:
        problems.append("blob exceeds 5 MiB")
    if name == "data/metadata/dataset_registry.json" and re.search(rb'"sample"\s*:', content):
        problems.append("individual source examples must stay local; run scripts/sanitize_registry.py")
    for label, pattern in PATTERNS.items():
        if re.search(pattern, content):
            problems.append(label)
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--ref", default="HEAD", help="HEAD or a full commit SHA to inspect before push")
    args = parser.parse_args()
    if args.ref != "HEAD" and not re.fullmatch(r"[0-9a-f]{40}", args.ref):
        parser.error("--ref must be HEAD or a full commit SHA")
    failures = []
    count = 0
    largest = (0, "")
    if args.history:
        objects = git("rev-list", "--objects", args.ref).decode().splitlines()
        entries = [(line.split(" ", 1)[1], line.split(" ", 1)[0])
                   for line in objects if " " in line]
    else:
        names = git("ls-files", "-z").decode().split("\0")
        entries = [(name, ":" + name) for name in names if name]
    for name, ref in entries:
        if args.history and git("cat-file", "-t", ref).strip() != b"blob":
            continue
        content = git("show", ref)
        count += 1
        largest = max(largest, (len(content), name))
        for problem in inspect(name, content):
            failures.append(f"{name}: {problem}")
    for failure in failures:
        print(failure)
    print(f"Checked {count} blobs; findings={len(failures)}; largest={largest[0]} bytes ({largest[1]})")
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
