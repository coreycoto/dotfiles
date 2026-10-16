#!/usr/bin/env python3
"""Back up the manifest's targets; restore originals without deleting new files."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile


REPO = Path(__file__).resolve().parents[1]
LOCAL_TARGETS = [
    ".gitconfig.local",
    ".config/zsh/options.local.zsh",
    ".config/zsh/local.zsh",
    ".codex/config.toml",
    ".config/dotfiles/agent-plugins.local.json",
    ".config/dotfiles/vscode/settings.local.json",
]


def relative_target(value):
    target = Path(value)
    if target.is_absolute() or not target.parts or ".." in target.parts:
        raise ValueError("Backup target must be a relative home path")
    return target


def create(home_dir, backup_dir):
    entries = json.loads((REPO / "manifest.json").read_text())["files"]
    targets = [entry["target"] for entry in entries] + LOCAL_TARGETS
    backup_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    receipt = {"version": 1, "files": {}}
    for value in targets:
        target = relative_target(value)
        live = home_dir / target
        if live.is_symlink():
            receipt["files"][value] = {"kind": "symlink", "link": os.readlink(live)}
        elif not live.exists():
            receipt["files"][value] = {"kind": "absent"}
        elif stat.S_ISREG(live.stat().st_mode):
            saved = backup_dir / "files" / target
            saved.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            shutil.copyfile(live, saved)
            saved.chmod(0o600)
            receipt["files"][value] = {
                "kind": "file",
                "mode": stat.S_IMODE(live.stat().st_mode),
                "sha256": hashlib.sha256(saved.read_bytes()).hexdigest(),
            }
        else:
            raise ValueError(f"Expected a file or symlink at {target}")
    (backup_dir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"Created private backup: {backup_dir}")


def restore(home_dir, backup_dir):
    receipt = json.loads((backup_dir / "receipt.json").read_text())
    if receipt.get("version") != 1:
        raise ValueError("Unsupported backup version")
    allowed = {
        entry["target"]
        for entry in json.loads((REPO / "manifest.json").read_text())["files"]
    } | set(LOCAL_TARGETS)
    prepared = []
    # Validate the whole receipt before changing any destination file.
    for value, entry in receipt["files"].items():
        if value not in allowed:
            raise ValueError("Backup contains a target outside the manifest")
        live = home_dir / relative_target(value)
        if entry["kind"] == "absent":
            continue
        if live.exists() and not live.is_symlink() and not live.is_file():
            raise ValueError(f"Refusing to replace a directory at {value}")
        if entry["kind"] == "file":
            saved = backup_dir / "files" / value
            if hashlib.sha256(saved.read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError(f"Backup checksum failed for {value}")
        elif entry["kind"] != "symlink":
            raise ValueError("Unknown backup entry type")
        prepared.append((value, entry, live))
    for value, entry, live in prepared:
        live.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".dotfiles-restore-", dir=live.parent)
        os.close(fd)
        try:
            if entry["kind"] == "file":
                shutil.copyfile(backup_dir / "files" / value, temporary)
                os.chmod(temporary, entry["mode"])
            else:
                os.unlink(temporary)
                os.symlink(entry["link"], temporary)
            os.replace(temporary, live)
        finally:
            if os.path.lexists(temporary):
                os.unlink(temporary)
    print("Restored original files and symlinks. Newly created targets were left in place.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["create", "restore"])
    parser.add_argument("--home", required=True, type=Path)
    parser.add_argument("--backup", required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    if not args.home.is_dir():
        parser.error("--home must identify an existing home directory")
    backup_dir = args.backup.resolve()
    if backup_dir == REPO or REPO in backup_dir.parents:
        parser.error("Keep backups outside the source repository")
    operation = create if args.operation == "create" else restore
    operation(args.home.resolve(), backup_dir)


if __name__ == "__main__":
    main()
