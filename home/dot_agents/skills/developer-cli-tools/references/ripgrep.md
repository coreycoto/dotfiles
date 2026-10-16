# ripgrep: contents and paths

From an explicit repository working directory:

```sh
# Filename discovery; use fd for richer filename predicates if available.
rg --no-config --files -g '*.py' src tests
# Literal content search with line numbers and stable agent output.
rg --no-config -n --color never -F -e 'parse_config' -- src tests
# Return only paths containing a match.
rg --no-config -l -F -e 'parse_config' -- src tests
# Inspect hidden workflow files without traversing the entire repository.
rg --no-config --hidden -n --color never -e 'python-version' -- .github
```

Use `-F` for literal text, `-e` for a pattern that could start with a dash, and
`--` before path operands. `--no-config` avoids user ripgrep configuration
changing automated behavior.

Ignored and hidden files are omitted by default. `--hidden` includes hidden
files but still respects ignore rules; `--no-ignore` also changes ignore
behavior. Enable either only for the scoped paths the task requires.

For a filename pipeline, `rg --files -0` emits NUL-delimited paths. Don't feed
ordinary newline-delimited search output to `xargs` when names can contain
spaces or newlines. Review a search result before treating it as an edit target.

Exit status `0` means a match, `1` means no match, and `2` means an error. A
permission error or missing search path does not prove absence. Avoid blindly
appending `|| true` or truncating output before distinguishing those cases.

Fallback: `git grep -n -F -e 'parse_config' -- src tests` searches tracked files;
it is not equivalent to searching untracked working-tree files.

Source: [ripgrep guide](https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md).
