# gh: explicit repository and remote evidence

Use the available connector for PR/issue lifecycle operations. When gh is the
appropriate surface, set the repository explicitly rather than relying on an
unrelated current checkout. Replace the placeholders below:

```sh
gh pr view NUMBER --repo OWNER/REPO \
  --json number,state,headRefOid,baseRefName,isDraft,statusCheckRollup
gh pr checks NUMBER --repo OWNER/REPO
gh run view RUN_ID --repo OWNER/REPO --log-failed
```

Check the PR's `headRefOid` against the intended commit and the workflow run's
revision. Pending, skipped, cancelled, and failed checks are not interchangeable
with passing checks. Check results do not establish merge, release, or deployment
completion; read the relevant product state separately.

For an authorized publication, use local Git to push the validated branch and
reuse an existing matching open PR. Prefer the installed publishing workflow's
connector operations for title/body and state changes. If an actual connector
gap requires gh, use `--body-file` with a UTF-8 file for multiline text; don't
interpolate prose or JSON into shell code. Use `gh api --input` for structured
JSON when the CLI lacks a matching command.

`gh auth status` diagnoses the selected account when a CLI fallback is needed.
Do not print tokens with `gh auth token` or copy credentials into a command.
A command-scoped `git -c credential.helper= -c 'credential.helper=!gh auth git-credential'`
can use the existing gh login for an authorized Git operation when Git's helper
is unavailable; it does not require changing global Git configuration.

Sources: [PR checks](https://cli.github.com/manual/gh_pr_checks),
[PR view](https://cli.github.com/manual/gh_pr_view),
[API](https://cli.github.com/manual/gh_api).
