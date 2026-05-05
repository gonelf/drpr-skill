---
name: drpr
description: "Publish files to drpr.host and get a shareable live URL. Trigger on: share this, publish this, give me a link, host this, drpr. Only works in Claude Code — if in claude.ai respond: this skill only works in Claude Code."
allowed-tools: Bash(python3 *)
---

## Rules — never override

1. Never upload anonymously. No auth = no upload. Always login first.
2. Never write inline upload code. Use drpr MCP tools only: drpr_status, drpr_login, drpr_upload, drpr_logout.
3. Never check $DRPR_API_KEY. The MCP server manages the key.
4. If login fails, stop. Never upload.

---

## Workflow

### Step 1 — check auth

Call `drpr_status`.
- `authenticated:EMAIL` → skip to step 3
- anything else → step 2

### Step 2 — login

Call `drpr_login`.
- `already_authenticated` → step 3
- `browser_opened:URL` → tell the user:
  > "I've opened drpr.host in your browser — please register or log in. I'm polling and will continue automatically once you're done."
  Wait. The tool polls every 2s automatically.
- `open_browser:URL` → tell the user:
  > "Please open this URL to log in: URL"
  Wait for confirmation, then call `drpr_login` again.
- `authenticated:KEY...` → say "You're logged in!" → step 3
- `error:login_expired` or `error:login_timeout` → tell the user and offer to try again. Stop.
- `error:*` → surface the error. Stop. Never upload.

### Step 3 — upload

Derive a subdomain from the filename: lowercase, hyphens only, 3–50 chars.
Example: `shampoo-landing.html` → `shampoo-landing`

Call `drpr_upload` with `file_path` (absolute path) and `subdomain`.

- `uploaded:URL` → tell the user:
  > "Published → URL"
- `error:not_authenticated` → go to step 1
- `error:unauthorized` → call `drpr_login` with `force=true`, then retry upload
- `error:http_409:*` → append a 4-char random suffix to subdomain and retry
- `error:file not found:*` → tell the user the path doesn't exist
- `error:*` → surface the error

---

## Proactive offer

After creating any shareable file (HTML page, PDF, report, demo), offer:
> "Want me to publish this on drpr so you can share a link?"

---

## Logout

If the user asks to log out or switch accounts, call `drpr_logout`.
