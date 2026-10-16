#!/usr/bin/env python3
"""Preview or apply personal Codex preferences and the reviewed plugin selection."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


REPO = Path(__file__).resolve().parents[1]
HELPERS = ("codex-preferences", "agent-plugins")


def setup(home, codex, apply, *, runner=subprocess.run):
    report = {"status": "preview", "applied": False, "steps": []}
    phases = (False, True) if apply else (False,)
    for applying in phases:
        for helper in HELPERS:
            command = [sys.executable, str(REPO / "scripts" / f"{helper}.py"),
                       "--home", str(home)]
            if codex:
                command += ["--codex", codex]
            if applying:
                command.append("--apply")
            step = {"helper": helper, "phase": "apply" if applying else "preview"}
            report["steps"].append(step)
            try:
                result = runner(command, text=True, capture_output=True)
                step["exit_code"] = result.returncode
                try:
                    step["receipt"] = json.loads(result.stdout)
                except (ValueError, TypeError):
                    step["receipt_unavailable"] = True
                if result.returncode or "receipt_unavailable" in step:
                    raise ValueError("Helper did not establish successful completion")
            except (OSError, ValueError, subprocess.SubprocessError):
                report["status"] = "failed"
                report["failed_step"] = step
                report["next_action"] = (
                    "Inspect this helper and the retained receipts before another attempt. "
                    "Earlier apply steps may have completed; no operation was retried."
                )
                return report, 2
    report["applied"] = apply
    report["status"] = "applied" if apply else "preview"
    report["next_action"] = (
        "Open each updated plugin's Setup in Codex. Complete hook review and the native agent forms; restart when the installer asks."
        if apply else "Review the preview, then use the same command with --apply."
    )
    return report, 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--codex", default=shutil.which("codex"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.home.is_dir():
        parser.error("--home must name an existing user home")
    report, code = setup(args.home.resolve(), args.codex, args.apply)
    print(json.dumps(report, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
