#!/usr/bin/env python3
"""Preview or atomically merge personal defaults and an additive reviewer policy."""

import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import tempfile
import tomllib


REPO = Path(__file__).resolve().parents[1]
KEYS = {
    "model", "model_reasoning_effort", "plan_mode_reasoning_effort", "personality", "service_tier",
    "approval_policy", "approvals_reviewer", "default_permissions",
    "memories.extract_model", "memories.consolidation_model",
    "desktop.followUpQueueMode", "desktop.composerEnterBehavior", "desktop.dock-icon-preference",
    "desktop.conversationDetailMode", "desktop.open-link-in-target-preference",
}
BOOL_KEYS = {
    "features.mcp_2026_07_28", "features.multi_agent", "features.fast_mode", "features.memories",
    "features.goals", "features.js_repl", "memories.generate_memories", "memories.use_memories",
    "memories.disable_on_external_context", "desktop.preventSleepWhileRunning",
    "desktop.keepRemoteControlAwakeWhilePluggedIn", "desktop.git-create-pull-request-as-draft",
    "desktop.git-show-sidebar-pr-icons", "desktop.show-context-window-usage",
}
ACCESS_DEFAULTS = {
    "approval_policy": "on-request", "approvals_reviewer": "auto_review", "default_permissions": ":workspace",
}
POLICY_KEY = "auto_review.extra_policy"
DEFAULT_PREFERENCES = REPO / "home/dot_codex/preferences.toml.tmpl"
NATIVE = runpy.run_path(str(REPO / "home/dot_local/bin/executable_dotfiles-plugins"))
Rpc = NATIVE["Rpc"]


def preference_text(path):
    if path.resolve() != DEFAULT_PREFERENCES.resolve():
        return path.read_text()
    chezmoi = shutil.which("chezmoi")
    if not chezmoi:
        raise ValueError("chezmoi is required to render managed preferences")
    with tempfile.TemporaryDirectory(prefix="dotfiles-preferences-render-") as scratch:
        state = Path(scratch)
        config = state / "chezmoi.json"
        config.write_text("{}\n")
        result = subprocess.run([
            chezmoi, "--source", str(REPO), "--config", str(config),
            "--persistent-state", str(state / "state.db"), "--cache", str(state / "cache"),
            "--no-tty", "execute-template", "--file", str(path),
        ], capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise ValueError("Unable to render managed preferences")
        return result.stdout


def preferences(path):
    data = tomllib.loads(preference_text(path))
    flat = {}

    def flatten(table, prefix=""):
        for key, value in table.items():
            leaf = prefix + key
            if isinstance(value, dict):
                if not value:
                    raise ValueError("Empty configuration tables are not portable preferences")
                flatten(value, leaf + ".")
            else:
                flat[leaf] = value

    flatten(data)
    if set(flat) != KEYS | BOOL_KEYS | {POLICY_KEY}:
        raise ValueError("Preferences must contain only the declared portable leaf keys")
    if any(not isinstance(flat[k], str) or not flat[k].strip() for k in KEYS):
        raise ValueError("Portable defaults must be non-empty strings")
    if any(type(flat[k]) is not bool for k in BOOL_KEYS):
        raise ValueError("Portable switches must be booleans")
    if any(flat[k] != value for k, value in ACCESS_DEFAULTS.items()):
        raise ValueError("Only the built-in workspace profile with automatic approval review is portable")
    policy = flat[POLICY_KEY]
    if not isinstance(policy, str) or not policy.strip():
        raise ValueError("The reviewer supplement must be a non-empty string")
    return flat


def value_at_path(data, key):
    value = data
    for part in key.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def expected_configuration(before, desired):
    after = copy.deepcopy(before)
    for key, value in desired.items():
        table = after
        *parents, leaf = key.split(".")
        for part in parents:
            table = table.setdefault(part, {})
            if not isinstance(table, dict):
                raise ValueError("The current reviewer configuration must be a table")
        table[leaf] = value
    return after


def require_compatible_codex(codex):
    result = subprocess.run([codex, "--version"], capture_output=True, text=True, timeout=15)
    match = re.fullmatch(r"codex-cli (\d+)\.(\d+)\.(\d+)(?:[-+][^\s]+)?", result.stdout.strip())
    if result.returncode or match is None or tuple(map(int, match.groups())) < (0, 162, 0):
        raise ValueError("Codex 0.162.0 or later is required for the portable preferences")



def merge(home, desired, codex, apply):
    target = home / ".codex/config.toml"
    if (home / ".codex").is_symlink() or target.is_symlink():
        raise ValueError("Refusing a symlinked Codex configuration")
    before = tomllib.loads(target.read_text()) if target.exists() else {}
    expected = expected_configuration(before, desired)
    changed = {k: v for k, v in desired.items() if value_at_path(before, k) != v}
    report = {"applied": False, "changed_keys": sorted(changed), "target": str(target)}
    if not apply or not changed:
        return report
    if not codex:
        raise ValueError("A compatible Codex executable is required to apply preferences")
    require_compatible_codex(codex)
    (home / ".codex").mkdir(mode=0o700, exist_ok=True)
    rpc = Rpc(codex, home)
    try:
        rpc.call("initialize", {"clientInfo": {"name": "dotfiles-preferences", "version": "1"}})
        rpc.process.stdin.write(json.dumps({"method": "initialized"}) + "\n")
        rpc.process.stdin.flush()
        observed = rpc.call("config/read", {"includeLayers": True, "cwd": str(home)})
        layer = next((x for x in observed.get("layers") or []
                      if x["name"].get("type") == "user"
                      and x["name"].get("file") == str(target)
                      and not x["name"].get("profile")), None)
        if layer is None or layer["config"] != before:
            raise ValueError("Codex user configuration changed or its version is unavailable")
        if target.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
            backup = home / ".local/state/dotfiles/backups" / (stamp + "-codex-preferences")
            backup.mkdir(mode=0o700, parents=True, exist_ok=False)
            saved = backup / "config.toml"
            shutil.copyfile(target, saved)
            saved.chmod(0o600)
            report["backup"] = str(backup)
        result = rpc.call("config/batchWrite", {
            "edits": [{"keyPath": k, "value": v, "mergeStrategy": "replace"} for k, v in changed.items()],
            "filePath": str(target), "expectedVersion": layer["version"], "reloadUserConfig": False,
        })
        after = tomllib.loads(target.read_text())
        if after != expected:
            raise ValueError("Post-write verification failed; retain the private backup and inspect locally")
        report.update(applied=True, status=result["status"])
        return report
    finally:
        rpc.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--preferences", type=Path, default=DEFAULT_PREFERENCES)
    parser.add_argument("--codex", default=shutil.which("codex"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if not args.home.is_dir():
            raise ValueError("--home must name an existing user home")
        report = merge(args.home.resolve(), preferences(args.preferences), NATIVE["resolve_codex"](args.codex), args.apply)
    except (OSError, ValueError, tomllib.TOMLDecodeError, subprocess.TimeoutExpired):
        parser.exit(2, "Preference operation failed; inspect local inputs without publishing configuration.\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
