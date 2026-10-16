#!/usr/bin/env python3
"""Run the same plugin updater shipped as dotfiles-plugins."""
from pathlib import Path
import runpy

REPO = Path(__file__).resolve().parents[1]
globals().update({name: value for name, value in runpy.run_path(
    str(REPO / "home/dot_local/bin/executable_dotfiles-plugins")).items()
    if not name.startswith("__")})

if __name__ == "__main__":
    main(default_manifest=REPO / "home/dot_config/dotfiles/agent-plugins.json")
