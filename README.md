# PAX MODS — Happ Proxy Config Manager

- `index.html` — buyer page (login with key → encrypted Happ link, Copy, Add Subscription)
- `controlpanel.html` — admin panel (keys, settings, preview, downloads)
- `sync_configs.py` — generates `configs/{KEY}.json` from Firebase `/keys`
- `.github/workflows/sync.yml` — runs the sync every 5 min and commits changes

## Deploy on GitHub
1. Create a **public** repo and upload all files (keep the folder structure, including `.github/`).
2. **Settings → Pages →** Deploy from branch `main` / root. Your site: `https://USER.github.io/REPO/`
3. **Settings → Actions → General → Workflow permissions →** Read and write.
4. Run **Actions → Sync configs → Run workflow** once.
5. Config URLs become `https://USER.github.io/REPO/configs/{KEY}.json` (index.html detects this automatically).

## Before going live
- Change `ADMIN_PASS` in `controlpanel.html` (client-side only — not real security).
- Lock Firebase rules:
  `{"rules":{"keys":{"$k":{".read":true}},"settings":{".read":true},"keyConfigs":{".read":true},".write":false}}`
  and do admin writes via Firebase Auth / Admin SDK.
- Verify `CRYPT_API` in `index.html` against Happ's docs.
- GitHub cron can lag a few minutes, so expiry reflects in config files with a delay.
