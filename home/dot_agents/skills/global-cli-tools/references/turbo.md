# Turbo

Use the project-pinned Turbo and its scripts for monorepo tasks; the Mise global
is a fallback. Inspect package scripts and `turbo.json` before picking a task.

```sh
turbo --version
turbo run build --dry=json
turbo run test --filter=PACKAGE --dry=json
```

A dry run explains the selected graph, not whether tests pass. Review filters
and dependency expansion before execution. Actual tasks can generate output,
contact services, or deploy when project scripts do so. Cached success proves
reuse of a recorded result; check task inputs, environment declarations, and
revision before treating it as fresh execution. Do not use `--force` reflexively
or enable remote caching merely to resolve a local failure.

Source: [run reference](https://turborepo.com/docs/reference/run).
