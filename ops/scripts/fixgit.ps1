cd "C:\Dev\The Combine"
git reset HEAD ops/aws/task-def-microsoft.json
del ops\aws\task-def-microsoft.json
git add -A
git status
git commit -m "Fix auth testing issues: audit logging, redirects, and account picker

- Fix logout audit log to capture user_id before session deletion
- Add missing AuthEventType enums: ACCOUNT_UNLINKED, LINK_BLOCKED_IDENTITY_EXISTS
- Fix account linking redirects (was /static/accounts.html, now /)
- Add prompt=select_account to OAuth flows (always show account picker)
- Remove duplicate app/auth/accounts.py (unused)"
git push