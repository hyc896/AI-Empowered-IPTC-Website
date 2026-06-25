# Git Structure And Release Notes

This repository is currently a mixed structure:

- Root repository: `AI-Empowered-IPTC-Website`, branch `master`
- `二期/`: normal directory tracked by the root repository
- `一期/`: Git submodule tracked by the root repository, branch `main`

The submodule points to the same GitHub repository URL as the root repo. That
means a server-side `git pull` in the root repository does not automatically
update `一期/` unless submodules are also updated.

## Current Release Flow

Use this order:

1. Commit and push `一期/` changes from inside `一期/`.
2. Commit and push root changes, including the updated `一期` submodule pointer.
3. On the server, run:

```bash
git pull
bash update_server.sh
```

`update_server.sh` now runs:

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

so the server should pull the exact submodule commit recorded by the root repo.

## Do Not Use

Do not run these from the root project:

```bash
git add .
git add -A
```

The working tree contains historical deletions, generated files, ChromaDB
binary changes, and old frontend artifacts. A broad add will upload unrelated
or oversized data.

## Safe Staging

Use the helper script:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stage-deploy-fix.ps1
```

It shows the exact files intended for the deployment fix. To stage them:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stage-deploy-fix.ps1 -Stage
```

## Recommended Cleanup Direction

The clean long-term structure is a monorepo:

```text
AI-Empowered-IPTC-Website/
  一期/
  二期/
  docker-compose.yml
  update_server.sh
```

To get there safely, first make one clean deployment fix commit with the current
submodule structure. Then migrate `一期/` into the root repository in a dedicated
cleanup branch, with ChromaDB, logs, caches, and generated assets excluded.
