#!/usr/bin/env python3
"""Preview portable VS Code settings or pinned extensions; --apply changes them."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys
import tempfile


REPO = Path(__file__).resolve().parents[1]
SELECTION = REPO / "home/dot_config/dotfiles/vscode"
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|//[^\r\n]*|/\*[\s\S]*?\*/|\s+|[{}\[\],:]|[^\s{}\[\],:\"/]+')


def reject_constant(value):
    raise ValueError("Non-JSON number in settings")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key; review the file before merging")
        result[key] = value
    return result


def jsonc(text):
    """Parse JSONC and retain token positions for edits to top-level values only."""
    tokens, cleaned, position = [], list(text), 0
    for match in TOKEN.finditer(text):
        if match.start() != position:
            raise ValueError("Malformed JSONC")
        token = match.group()
        position = match.end()
        if token.startswith(("//", "/*")):
            cleaned[match.start():match.end()] = [
                character if character in "\r\n" else " " for character in token
            ]
        elif not token.isspace():
            tokens.append((token, match.start(), match.end()))
    if position != len(text):
        raise ValueError("Malformed JSONC")
    for index, token in enumerate(tokens[:-1]):
        if (token[0] == "," and index > 0 and tokens[index - 1][0] not in ("{", "[", ",", ":")
                and tokens[index + 1][0] in ("}", "]")):
            cleaned[token[1]] = " "
    try:
        value = json.loads("".join(cleaned), object_pairs_hook=unique_object,
                           parse_constant=reject_constant)
    except json.JSONDecodeError as error:
        raise ValueError(f"Malformed JSONC at line {error.lineno}; review it locally") from None
    if not isinstance(value, dict):
        raise ValueError("Settings must be a JSON object")
    return value, tokens


def merge_settings(original, selected):
    current, tokens = jsonc(original)
    edits, present, index = [], set(), 1
    last_value_end = None
    while tokens[index][0] != "}":
        key = json.loads(tokens[index][0])
        start = index + 2
        end, depth = start, 0
        while end < len(tokens):
            token = tokens[end][0]
            if depth == 0 and token in (",", "}"):
                break
            if token in ("{", "["):
                depth += 1
            elif token in ("}", "]"):
                depth -= 1
            end += 1
        last_value_end = tokens[end - 1][2]
        present.add(key)
        if key in selected and json.dumps(current[key], sort_keys=True) != json.dumps(selected[key], sort_keys=True):
            edits.append((tokens[start][1], last_value_end,
                          json.dumps(selected[key], ensure_ascii=False)))
        index = end + 1 if tokens[end][0] == "," else end
    missing = [key for key in selected if key not in present]
    newline = "\r\n" if "\r\n" in original else "\n"
    if missing:
        separator = present and tokens[index - 1][0] != ","
        prefix = ""
        if separator:
            if last_value_end == tokens[index][1]:
                prefix = ","
            else:
                edits.append((last_value_end, last_value_end, ","))
        entries = ("," + newline).join(
            "  " + json.dumps(key) + ": " + json.dumps(selected[key], ensure_ascii=False)
            for key in missing
        )
        edits.append((tokens[index][1], tokens[index][1], prefix + newline + entries + newline))
    merged = original
    for start, end, replacement in sorted(edits, reverse=True):
        merged = merged[:start] + replacement + merged[end:]
    result, _ = jsonc(merged)
    if result != current | selected:
        raise ValueError("Settings merge validation failed")
    changed = [key for key in selected if key not in current or
               json.dumps(current[key], sort_keys=True) != json.dumps(selected[key], sort_keys=True)]
    return merged, changed


def outside_repo(path):
    path = path.expanduser().absolute()
    if path.resolve() == REPO or REPO in path.resolve().parents:
        raise ValueError("Keep editor state and backups outside the source repository")
    return path


def regular_file(path):
    if path.is_symlink():
        raise ValueError("Refusing a symlink; select its reviewed destination explicitly")
    if path.exists() and not path.is_file():
        raise ValueError("Expected a regular settings file")


def private_write(path, content):
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def operation_directory(state_dir):
    state_dir = outside_repo(state_dir)
    if state_dir.is_symlink():
        raise ValueError("Backup directory must not be a symlink")
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not state_dir.is_dir() or stat.S_IMODE(state_dir.stat().st_mode) & 0o077:
        raise ValueError("Backup directory must be private (mode 700)")
    return Path(tempfile.mkdtemp(prefix="apply-", dir=state_dir))


def save_receipt(directory, receipt):
    private_write(directory / "receipt.json", (json.dumps(receipt, indent=2) + "\n").encode())


def default_settings():
    if sys.platform == "darwin":
        base = Path.home() / "Library/Application Support/Code"
    elif sys.platform == "win32":
        base = Path(os.environ["APPDATA"]) / "Code"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "Code"
    return base / "User/settings.json"


def settings(args):
    target = outside_repo(args.settings_file or default_settings())
    regular_file(target)
    selected, _ = jsonc((SELECTION / "settings.json").read_text())
    overlay = (args.local_settings or Path.home() / ".config/dotfiles/vscode/settings.local.json").expanduser()
    if args.local_settings and not overlay.exists() and not overlay.is_symlink():
        raise ValueError("The explicitly selected local settings file is missing")
    if overlay.exists() or overlay.is_symlink():
        regular_file(overlay)
        local, _ = jsonc(overlay.read_text())
        selected.update(local)
    existed = target.exists()
    before = target.read_bytes() if existed else None
    merged, changed = merge_settings(before.decode("utf-8") if existed else "{}\n", selected)
    print(f"Settings target: {target}")
    print("Changed keys: " + (", ".join(changed) or "none"))
    if not args.apply or not changed:
        return
    directory = operation_directory(args.state_dir)
    receipt = {"operation": "settings", "target": str(target), "existed": existed,
               "status": "prepared", "changed_keys": changed}
    if existed:
        receipt.update(mode=stat.S_IMODE(target.stat().st_mode),
                       sha256=hashlib.sha256(before).hexdigest())
        private_write(directory / "settings.before.json", before)
    save_receipt(directory, receipt)
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    regular_file(target)
    if target.exists() != existed or (existed and target.read_bytes() != before):
        raise ValueError(f"Settings changed during preview; backup retained at {directory}")
    fd, temporary = tempfile.mkstemp(prefix=".dotfiles-vscode-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(merged.encode("utf-8"))
        os.chmod(temporary, receipt.get("mode", 0o600))
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    receipt["status"] = "applied"
    save_receipt(directory, receipt)
    print(f"Private backup and receipt: {directory}")


def extension_selection():
    selected = json.loads((SELECTION / "extensions.json").read_text(), object_pairs_hook=unique_object)
    if not selected or not all(
        re.fullmatch(r"[a-z0-9][a-z0-9-]*\.[a-z0-9][a-z0-9-]*", name)
        and isinstance(version, str) and re.fullmatch(r"\d+\.\d+\.\d+", version)
        for name, version in selected.items()
    ):
        raise ValueError("Extension selection must use qualified IDs and exact stable versions")
    return selected


def extension_inventory(output):
    result = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"([A-Za-z0-9-]+\.[A-Za-z0-9-]+)@(\d+\.\d+\.\d+(?:[-+][\w.-]+)?)", line.strip())
        if not match or match[1].lower() in result:
            raise ValueError("Unexpected extension inventory; review the private CLI log")
        result[match[1].lower()] = match[2]
    return result


def extensions(args):
    selected = extension_selection()
    command = [args.code]
    for flag, value in [("--user-data-dir", args.user_data_dir),
                        ("--extensions-dir", args.extensions_dir), ("--profile", args.profile)]:
        if value is not None:
            command += [flag, str(outside_repo(value)) if isinstance(value, Path) else value]
    install_flags = ["--force", "--do-not-sync", "--do-not-include-pack-dependencies"]
    for name, version in selected.items():
        print(shlex.join(command + ["--install-extension", f"{name}@{version}"] + install_flags))
    if not args.apply:
        return
    if os.environ.get("VSCODE_PORTABLE"):
        raise ValueError("Portable mode overrides directory selection; use a standard VS Code installation")
    env = os.environ.copy()
    for key in ("VSCODE_IPC_HOOK_CLI", "VSCODE_EXTENSIONS"):
        env.pop(key, None)
    directory = operation_directory(args.state_dir)
    receipt = {"operation": "extensions", "status": "started", "selection": selected,
               "selectors": command, "completed": []}
    save_receipt(directory, receipt)
    calls = 0

    def run(extra):
        nonlocal calls
        calls += 1
        result = subprocess.run(command + extra, env=env, capture_output=True, text=True, timeout=180)
        private_write(directory / f"cli-{calls}.log", (result.stdout + result.stderr).encode())
        if result.returncode:
            raise ValueError(f"VS Code command failed; review private log cli-{calls}.log")
        return result.stdout

    try:
        version = run(["--version"]).splitlines()[0]
        match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
        if not match or tuple(map(int, match.groups())) < (1, 100, 0):
            raise ValueError("The selected extensions require VS Code 1.100 or newer")
        before = extension_inventory(run(["--list-extensions", "--show-versions"]))
        receipt.update(code_version=version, before=before)
        save_receipt(directory, receipt)
        for name, version in selected.items():
            if before.get(name) == version:
                continue
            run(["--install-extension", f"{name}@{version}"] + install_flags)
            receipt["completed"].append(name)
            save_receipt(directory, receipt)
        after = extension_inventory(run(["--list-extensions", "--show-versions"]))
        receipt["after"] = after
        if any(after.get(name) != version for name, version in selected.items()):
            raise ValueError("Installed extension versions differ from the selection")
        if any(after.get(name) != version for name, version in before.items() if name not in selected):
            raise ValueError("An unrelated extension changed; review the private before/after receipt")
        receipt["status"] = "applied"
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        receipt["status"] = "incomplete"
        save_receipt(directory, receipt)
        print(f"Incomplete operation; private receipt: {directory}", file=sys.stderr)
        if isinstance(error, subprocess.TimeoutExpired):
            raise ValueError("VS Code command timed out; inspect the profile before retrying") from None
        raise
    save_receipt(directory, receipt)
    print(f"Verified selected versions; private receipt: {directory}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    operations = parser.add_subparsers(dest="operation", required=True)
    settings_parser = operations.add_parser("settings", help="Merge into the selected settings file")
    settings_parser.add_argument("--settings-file", type=Path)
    settings_parser.add_argument("--local-settings", type=Path)
    extensions_parser = operations.add_parser("extensions", help="Install only the pinned selection")
    extensions_parser.add_argument("--code", default="code")
    extensions_parser.add_argument("--user-data-dir", type=Path)
    extensions_parser.add_argument("--extensions-dir", type=Path)
    extensions_parser.add_argument("--profile", help="An existing named profile; omit for Default")
    for operation in (settings_parser, extensions_parser):
        operation.add_argument("--apply", action="store_true")
        operation.add_argument("--state-dir", type=Path, default=Path.home() / ".local/state/dotfiles/vscode")
    args = parser.parse_args()
    try:
        (settings if args.operation == "settings" else extensions)(args)
    except (ValueError, OSError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
