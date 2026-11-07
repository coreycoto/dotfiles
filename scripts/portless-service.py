#!/usr/bin/env python3
"""Explicitly install a durable Portless runtime or prepare an existing macOS service repair."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import tomllib

REPO = Path(__file__).resolve().parents[1]
SERVICE = Path("/Library/LaunchDaemons/sh.portless.proxy.plist")


def selection():
    package = json.loads((REPO / "tools/portless/package.json").read_text())
    version = package["dependencies"]["portless"]
    node = tomllib.loads((REPO / "home/dot_config/mise/config.toml").read_text())["tools"]["node"]
    return version, node


def runtime_tree(path):
    """Compare the complete published package; never adopt links or special files."""
    if path.is_symlink() or not path.is_dir():
        raise ValueError("Runtime must be an ordinary directory")
    if path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o022:
        raise ValueError("Runtime must be owned by the invoking user and not writable by others")
    result = {}
    for entry in path.rglob("*"):
        if entry.is_symlink() or not (entry.is_file() or entry.is_dir()):
            raise ValueError("Runtime contains a link or special file")
        if entry.stat().st_uid != os.getuid() or entry.stat().st_mode & 0o022:
            raise ValueError("Runtime files must be owned by the invoking user and not writable by others")
        if entry.is_file():
            result[str(entry.relative_to(path))] = entry.read_bytes()
    return result


def verified_runtime(path):
    files = runtime_tree(path)
    inventory = json.loads((REPO / "tools/portless/runtime.json").read_text())
    if inventory["version"] != selection()[0]:
        raise ValueError("Runtime integrity inventory and package selection disagree")
    marker = files.pop(".atelier-installation.json", None)
    actual = {name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
              for name, data in files.items()}
    if actual != inventory["files"]:
        raise ValueError("Runtime package bytes differ from the reviewed integrity inventory")
    if marker is not None:
        receipt = json.loads(marker)
        if not isinstance(receipt, dict):
            raise ValueError("Unrecognized prior service-repair marker")
        entries = receipt.get("files", [])
        if (receipt.get("version") != 1 or receipt.get("repository") != "coreycoto/atelier"
                or receipt.get("task") != 148 or receipt.get("purpose") != "portless-service-repair-proposal"
                or receipt.get("target") != str(path) or receipt.get("sourcePackageVersion") != inventory["version"]
                or not isinstance(entries, list) or len(entries) != len(actual)
                or any(not isinstance(entry, dict) for entry in entries)):
            raise ValueError("Unrecognized prior service-repair marker")
        recorded = {entry.get("path"): {"bytes": entry.get("bytes"), "sha256": entry.get("sha256")}
                    for entry in entries}
        if recorded != actual or any(entry.get("mode") != ((path / entry["path"]).stat().st_mode & 0o777)
                                     for entry in entries):
            raise ValueError("Prior service-repair marker does not match the complete package")
        if (path / ".atelier-installation.json").stat().st_mode & 0o111:
            raise ValueError("Service-repair marker must not be executable")
    return files


def validate_runtime_parents(home):
    # A root service must not follow a replaceable user runtime directory.
    for directory in (home, home / ".local", home / ".local/share", home / ".local/share/portless"):
        if directory.is_symlink():
            raise ValueError("Runtime parent must not be a symlink")
        if directory.exists() and (not directory.is_dir() or directory.stat().st_uid != os.getuid()
                                   or directory.stat().st_mode & 0o022):
            raise ValueError("Runtime parents must be owned by the invoking user and not writable by others")


def install_runtime(home, bun):
    version, _ = selection()
    parent = home / ".local/share/portless"
    # Installation trees are local, never managed by chezmoi or replaced in place.
    validate_runtime_parents(home)
    parent.mkdir(parents=True, exist_ok=True)
    validate_runtime_parents(home)
    target = parent / version
    with tempfile.TemporaryDirectory(prefix=".install-", dir=parent) as scratch:
        stage = Path(scratch)
        for name in ("package.json", "bun.lock"):
            shutil.copyfile(REPO / "tools/portless" / name, stage / name)
        subprocess.run([bun, "install", "--frozen-lockfile", "--ignore-scripts"], cwd=stage, check=True)
        package = stage / "node_modules/portless"
        metadata = json.loads((package / "package.json").read_text())
        if metadata.get("name") != "portless" or metadata.get("version") != version or metadata.get("dependencies"):
            raise ValueError("Unexpected Portless package or unqualified runtime dependencies")
        expected = verified_runtime(package)
        if not expected.get("dist/cli.js"):
            raise ValueError("Portless CLI is missing")
        if target.exists() or target.is_symlink():
            if verified_runtime(target) != expected:
                raise ValueError("Existing runtime differs; preserve it and investigate before replacement")
        else:
            # Rename the verified package on the same filesystem, never merge it.
            package.rename(target)
    return target


def prepare(home, source, output):
    version, node_version = selection()
    runtime = home / ".local/share/portless" / version
    validate_runtime_parents(home)
    files = verified_runtime(runtime)
    metadata = json.loads(files.get("package.json", b"{}"))
    if metadata.get("name") != "portless" or metadata.get("version") != version or not files.get("dist/cli.js"):
        raise ValueError("Install the reviewed service runtime first")
    mise_data = Path(os.environ.get("MISE_DATA_DIR", str(home / ".local/share/mise")))
    node = mise_data / "installs/node" / node_version.split(".")[0] / "bin/node"
    actual = subprocess.run([str(node), "--version"], check=True, capture_output=True, text=True).stdout.strip()
    if actual != "v" + node_version:
        raise ValueError("Stable Mise Node major alias does not select the reviewed global version")
    actual = subprocess.run([str(node), str(runtime / "dist/cli.js"), "--version"], check=True, capture_output=True, text=True).stdout.strip()
    if actual != version:
        raise ValueError("Installed Portless version does not match the reviewed selection")
    if source.is_symlink() or not source.is_file():
        raise ValueError("Existing service must be an ordinary plist file")
    original = source.read_bytes()
    spec = plistlib.loads(original)
    args = spec.get("ProgramArguments", [])
    if (spec.get("Label") != "sh.portless.proxy" or len(args) < 5
            or args[2:5] != ["proxy", "start", "--foreground"]
            or spec.get("EnvironmentVariables", {}).get("HOME") != str(home)):
        raise ValueError("Service identity, user home or foreground command does not match; review manually")
    spec["ProgramArguments"] = [str(node), str(runtime / "dist/cli.js"), *args[2:]]
    candidate = plistlib.dumps(spec)
    # Caller chooses a new private staging directory; never touch live launchd.
    output.mkdir(mode=0o700)
    for name, data in (("original.plist", original), ("candidate.plist", candidate)):
        descriptor = os.open(output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
    receipt = {"service": str(source), "originalSha256": hashlib.sha256(original).hexdigest(),
               "candidateSha256": hashlib.sha256(candidate).hexdigest(),
               "node": str(node), "runtime": str(runtime), "applied": False}
    descriptor = os.open(output / "receipt.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("install-runtime", help="install the locked package; does not start or configure a service")
    repair = commands.add_parser("prepare", help="stage a path-only repair of the existing macOS service; does not apply it")
    repair.add_argument("--output", required=True, type=Path, help="new private staging directory")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("Run as the owning user, never with sudo")
    try:
        if args.command == "install-runtime":
            bun = shutil.which("bun")
            if not bun:
                raise ValueError("Install the reviewed Bun runtime first")
            print(install_runtime(Path.home(), bun))
        else:
            prepare(Path.home(), SERVICE, args.output)
            print(f"Prepared {args.output}; review the two plist paths and receipt before administrator application.")
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Portless service preparation failed: {error}\n")


if __name__ == "__main__":
    main()
