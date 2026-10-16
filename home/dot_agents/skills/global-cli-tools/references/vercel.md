# Vercel CLI

Prefer available Vercel connectors and the installed deployment workflow skill.
Use the CLI when it provides needed evidence or a concrete connector gap.

```sh
vercel --version
vercel --help
vercel inspect DEPLOYMENT_URL
```

Identify team, project, revision, deployment URL, and Preview versus Production
before acting. Inspection is evidence about that deployment, not proof of browser
behavior. `vercel link` writes project state; `vercel pull` writes configuration
and can retrieve secrets. Deployment and promotion publish changes and need the
corresponding task authorization. Never commit `.vercel`, downloaded environment
files, or login tokens. Keep runtime ownership separate from deployment selection.

Source: [CLI documentation](https://vercel.com/docs/cli).
