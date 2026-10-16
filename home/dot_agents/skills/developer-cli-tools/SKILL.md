---
name: developer-cli-tools
description: Choose and combine developer CLI tools for repository searches, file discovery, candidate selection, directory navigation, and file previews. Use when selecting a tool or composing a workflow with ripgrep, fd, fzf, zoxide, or bat.
---

# Developer CLI tools

Choose the tool by the question being answered; an installed command is not a
reason to introduce it into an otherwise simple task.

| Need | Preferred tool | Fallback |
|---|---|---|
| Search contents | `rg` | `git grep` for tracked files; `grep` for explicit files |
| Find filenames | `rg --files`; `fd` when available | `git ls-files` or scoped `find` |
| Let a person select candidates | `fzf` with an explicit input list | Show a short candidate list |
| Filter unattended candidates | `fzf --filter` for fuzzy matching | Exact/glob/regex matching when that is the actual requirement |
| Navigate remembered directories | `zoxide` in an interactive shell | Explicit `cd` or command working directory |
| Preview a file | `bat` | `sed` for a range; `cat` for the whole file |

Check `command -v` for the commands needed by the selected workflow. If a tool
is missing, use a fallback or describe the explicit installation needed; do not
run an installer as part of searching or reading files. Mise declares the
five tools, including `fd` for filename discovery.

## Choose the execution mode

- **Agent/CI:** set an explicit repository working directory, supply candidates
  explicitly, disable pagers and color in consumed output, and avoid interactive
  prompts. Fuzzy matches can contain multiple candidates; verify the exact path
  before acting on one. Zoxide's local ranking is not a reproducible selector.
- **Human terminal:** interactive fzf selection and zoxide navigation are useful.
  Their shell key bindings/functions require separate initialization; installing
  the binaries alone does not enable those integrations.

Scope searches to relevant files or directories first. Default ripgrep/fd
searches omit ignored and hidden files; decide whether that omission matters
before concluding a file or reference is absent. Prefer narrow globs and paths
over globally disabling ignore rules. Use NUL delimiters in filename pipelines
when names may contain newlines, and quote paths passed to later commands.

## Load only the relevant reference

- [ripgrep](references/ripgrep.md): content searches, filename discovery, ignore
  behavior, and interpreting no-match versus error results.
- [fd](references/fd.md): filename predicates and scoped discovery when available.
- [fzf](references/fzf.md): interactive selection, unattended filtering, and
  separating fuzzy discovery from exact selection.
- [zoxide](references/zoxide.md): remembered navigation and reproducible paths.
- [bat](references/bat.md): human previews and stable, pager-free agent output.

For a combined workflow, discover candidates, inspect the relevant matches, then
read a bounded file range. Do not convert candidate strings into shell code or
bulk edits; hand verified paths to the tool appropriate for the user's task.
