#!/usr/bin/env python3
"""Preview a staged Codex rule migration without changing the host."""

import argparse
import hashlib
import json
from pathlib import Path
import re


REPO = Path(__file__).resolve().parents[1]
BUNDLE = REPO / "home/dot_config/dotfiles/codex-rules"
NAMES = {"personal.rules", "legacy-project.rules"}
LEGACY = "coreycoto.com.rules"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state(home, relative):
    """Do not follow a symlink through the proposed migration's destinations."""
    path = home
    parts = Path(relative).parts
    for index, part in enumerate(parts):
        path = path / part
        if path.is_symlink():
            return {"state": "conflict", "reason": "symlink"}
        if index < len(parts) - 1 and path.exists() and not path.is_dir():
            return {"state": "conflict", "reason": "parent_not_directory"}
    if not path.exists():
        return {"state": "absent"}
    if not path.is_file():
        return {"state": "conflict", "reason": "not_file"}
    return {"state": "file", "sha256": digest(path)}


def preview(home, bundle=BUNDLE):
    if home.is_symlink() or not home.is_dir():
        raise ValueError("Expected a real home directory")
    if (bundle / "migration.json").is_symlink():
        raise ValueError("Expected a real migration manifest")
    metadata = json.loads((bundle / "migration.json").read_text())
    if not isinstance(metadata, dict) or not isinstance(metadata.get("files"), dict):
        raise ValueError("Unsupported migration manifest")
    if (metadata.get("version") != 1 or metadata.get("legacy_file") != LEGACY
            or set(metadata.get("files", {})) != NAMES):
        raise ValueError("Unsupported migration manifest")
    digests = [metadata.get("legacy_sha256"), *metadata["files"].values()]
    if any(not isinstance(value, str) or not re.fullmatch("[0-9a-f]{64}", value) for value in digests):
        raise ValueError("Invalid migration digest")
    for name, expected in metadata["files"].items():
        if (bundle / name).is_symlink() or digest(bundle / name) != expected:
            raise ValueError("Staged rule content differs from its reviewed digest")

    legacy = state(home, ".codex/rules/" + LEGACY)
    legacy["owned"] = (legacy.get("sha256") == metadata["legacy_sha256"])
    targets = []
    for name, expected in sorted(metadata["files"].items()):
        observed = state(home, ".codex/rules/" + name)
        if observed["state"] == "file":
            observed["state"] = "already_matches" if observed["sha256"] == expected else "conflict"
        targets.append({"name": name, "expected_sha256": expected, **observed})

    default = state(home, ".codex/rules/default.rules")
    conflict = (legacy["state"] == "conflict" or default["state"] == "conflict"
                or any(t["state"] == "conflict" for t in targets))
    status = "conflict" if conflict else "ready_for_review" if legacy["owned"] else "legacy_unverified"
    return {
        "status": status,
        "applied": False,
        "policy_revision": metadata.get("policy_revision", 1),
        "staged_counts": metadata.get("staged_counts"),
        "legacy": legacy,
        "targets": targets,
        "default_rules": default,
        "next_step": "Separate approval, private backup, current-state recheck and activation are required."
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    args = parser.parse_args()
    try:
        report = preview(args.home.absolute())
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"status": "invalid_source_or_unreadable_state", "applied": False}))
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "ready_for_review" else 2


if __name__ == "__main__":
    raise SystemExit(main())
