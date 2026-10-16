#!/usr/bin/env python3
"""Preview explicit project runtime selectors; --apply writes a Git-ignored file."""

import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile


SELECTOR = "mise.local.toml"
IGNORE = "/mise.local.toml"
TOOLS = {"node", "bun", "python", "rust", "tuist"}


def git(project, *args):
    return subprocess.run(
        ["git", "-C", str(project), *args], check=True,
        text=True, capture_output=True,
    ).stdout.strip()


def atomic_write(path, content, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".dotfiles-tools-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(content)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--tool", required=True, action="append", metavar="TOOL@VERSION")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    project = args.project.resolve(strict=True)
    if project != Path(git(project, "rev-parse", "--show-toplevel")).resolve():
        parser.error("--project must be the Git checkout root")
    tools = {}
    for spec in args.tool:
        name, separator, version = spec.partition("@")
        if (
            not separator or name not in TOOLS or name in tools
            or not re.fullmatch(r"\d+\.\d+\.\d+", version)
        ):
            parser.error("Use distinct supported tools with exact versions")
        tools[name] = version
    content = (
        "# Machine-local runtime selection. Project source and CI remain authoritative.\n"
        "[tools]\n" + "".join(f'{name} = "{version}"\n' for name, version in sorted(tools.items()))
    ).encode()
    target = project / SELECTOR
    exclude = Path(git(project, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude"))
    for path in (target, exclude):
        if path.is_symlink() or (path.exists() and not path.is_file()):
            parser.error("Refusing to replace a symlink or non-file")
    if target.exists() and target.read_bytes() != content:
        parser.error("Existing mise.local.toml differs; review it manually")
    if git(project, "ls-files", "--", SELECTOR):
        parser.error("Refusing to replace a tracked project configuration")
    print(json.dumps({"project": str(project), "target": str(target), "tools": tools,
                      "operation": "apply" if args.apply else "preview"}, indent=2))
    if args.apply:
        original = exclude.read_bytes() if exclude.exists() else b""
        if IGNORE.encode() not in original.splitlines():
            separator = b"" if not original or original.endswith(b"\n") else b"\n"
            mode = stat.S_IMODE(exclude.stat().st_mode) if exclude.exists() else 0o600
            atomic_write(exclude, original + separator + IGNORE.encode() + b"\n", mode)
        if not target.exists():
            atomic_write(target, content, 0o600)


if __name__ == "__main__":
    main()
