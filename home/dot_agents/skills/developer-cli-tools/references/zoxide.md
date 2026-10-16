# zoxide: interactive navigation

After the user enables shell integration, `z` jumps to a remembered directory
and `zi` opens interactive selection with fzf. The standalone binary can query
the same database:

```sh
zoxide query project-name
zoxide query --list project-name
```

Results depend on that machine's visit history and ranking. A fresh machine
may have no matching entry. Use a query to suggest locations to a person, then
verify the path and repository identity. For an agent task or CI job, use the
provided checkout and an explicit command working directory or `cd` instead
of guessing the checkout through ranking.

Installation does not populate the database or enable shell functions. Keep
the generated database outside Git. Use `zoxide init zsh` in the interactive
shell's reviewed local configuration when the user chooses integration; do not
add initialization or write visit history just to perform a repository search.

Source: [zoxide documentation](https://github.com/ajeetdsouza/zoxide).
