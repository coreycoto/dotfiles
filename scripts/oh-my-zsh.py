#!/usr/bin/env python3
"""Preview a pinned Oh My Zsh installation; --apply installs into a new directory."""

import argparse
from datetime import date
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


REPO = Path(__file__).resolve().parents[1]
UPSTREAM = "https://github.com/ohmyzsh/ohmyzsh.git"
REQUIRED_FILES = (
    "oh-my-zsh.sh", "LICENSE.txt", "lib/compfix.zsh",
    "tools/check_for_upgrade.sh", "plugins/git/git.plugin.zsh",
    "plugins/brew/brew.plugin.zsh", "plugins/dotenv/dotenv.plugin.zsh",
    "themes/robbyrussell.zsh-theme",
)


def load_pin():
    pin = json.loads((REPO / "tools/oh-my-zsh.json").read_text())
    if (
        set(pin) != {"repository", "revision", "reviewed_at"}
        or pin["repository"] != UPSTREAM
        or not isinstance(pin["revision"], str)
        or not re.fullmatch(r"[0-9a-f]{40}", pin["revision"])
    ):
        raise ValueError("The Oh My Zsh pin must select the official repository and a full commit ID.")
    date.fromisoformat(pin["reviewed_at"])
    return pin


def git(*args, cwd=None):
    return subprocess.run(
        ["git", "--no-optional-locks", "-c", "core.hooksPath=/dev/null",
         "-c", "core.fsmonitor=false", "-c", "init.templateDir=", *args],
        cwd=cwd, check=True, text=True, capture_output=True, timeout=120,
    ).stdout.strip()


def validate_files(destination):
    for name in REQUIRED_FILES:
        path = destination / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing regular Oh My Zsh file: {name}")


def validate_destination(destination):
    if not destination.is_absolute():
        raise ValueError("Use an absolute installation path.")
    if destination.resolve().is_relative_to(REPO):
        raise ValueError("Install Oh My Zsh outside the dotfiles source repository.")
    if destination.is_symlink():
        raise ValueError("The installation target is a symlink; preserve it and choose a new directory.")


def already_installed(destination, revision):
    if not destination.exists():
        return False
    if not destination.is_dir() or not (destination / ".git").is_dir() or (destination / ".git").is_symlink():
        raise ValueError("The destination already exists; preserve it and choose a new directory.")
    root = Path(git("rev-parse", "--show-toplevel", cwd=destination)).resolve()
    if root != destination.resolve() or git("rev-parse", "HEAD", cwd=destination) != revision:
        raise ValueError("An existing checkout has a different revision; use a new directory for migration or update.")
    if git("status", "--porcelain", "--untracked-files=no", cwd=destination):
        raise ValueError("Existing tracked files have changes; preserve them and choose a new directory.")
    validate_files(destination)
    return True


def install(pin, destination, *, apply=False):
    validate_destination(destination)
    revision = pin["revision"]
    if already_installed(destination, revision):
        print(f"Already at {revision}: {destination} (custom files retained)")
        return
    print(f"Install Oh My Zsh {revision} from {pin['repository']} into {destination}")
    if not apply:
        print("Preview only. Repeat with --apply to fetch and install.")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".dotfiles-oh-my-zsh-", dir=destination.parent) as scratch:
        checkout = Path(scratch) / "checkout"
        git("init", "--quiet", "--template=", str(checkout))
        git("remote", "add", "origin", pin["repository"], cwd=checkout)
        git("fetch", "--quiet", "--depth=1", "--no-tags", "origin", revision, cwd=checkout)
        if git("rev-parse", "FETCH_HEAD", cwd=checkout) != revision:
            raise ValueError("Fetched commit differs from the reviewed pin.")
        git("checkout", "--quiet", "--detach", revision, cwd=checkout)
        validate_files(checkout)
        # Reserve an absent destination exclusively after all network work succeeds.
        # An existing directory, even an empty one, is never replaced.
        destination.mkdir()
        try:
            checkout.rename(destination)
        except OSError:
            # Remove only our empty reservation, preserving any concurrent files.
            try:
                destination.rmdir()
            except OSError:
                pass
            raise
    print("Installed. Open a new shell after reviewing your local ZSH/ZSH_CUSTOM options.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination", type=Path,
        default=Path(os.environ.get("ZSH") or Path.home() / ".oh-my-zsh"),
        help="Absolute installation directory (default: exported ZSH, otherwise ~/.oh-my-zsh).",
    )
    parser.add_argument("--apply", action="store_true", help="Fetch and install the reviewed revision explicitly.")
    args = parser.parse_args()
    try:
        install(load_pin(), args.destination.expanduser(), apply=args.apply)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        # Do not relay Git diagnostics: a host's transport configuration may contain private values.
        if isinstance(error, subprocess.SubprocessError):
            message = "Git operation failed or timed out; the existing installation was preserved."
        else:
            message = str(error)
        parser.exit(2, f"Oh My Zsh installation failed: {message}\n")


if __name__ == "__main__":
    main()
