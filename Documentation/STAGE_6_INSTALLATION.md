# Stage 6: Account Linking - Installation Guide

## 📦 Step 1: Add Account Linking Methods to service.py

Open `app/auth/service.py` and add these imports at the top:

```python
from app.auth.db_models import LinkIntentNonceORM
```

Then **add all methods** from `account_linking_methods.py` to the `AuthService` class.
These methods go at the end of the class (after `log_auth_event`):

- `create_link_intent()`
- `verify_link_intent()`
- `link_oauth_identity()`
- `get_linked_identities()`
- `unlink_oauth_identity()`

## 📦 Step 2: Add New Event Types to models.py

Open `app/auth/models.py` and add to `AuthEventType` enum:

```python
    # Account linking events
    ACCOUNT_LINKED = "account_linked"
    ACCOUNT_UNLINKED = "account_unlinked"  # ← ADD THIS
    LINK_BLOCKED_IDENTITY_EXISTS = "link_blocked_identity_exists"  # ← ADD THIS
    LINK_CSRF_BLOCKED = "link_csrf_blocked"
    LINK_NONCE_INVALID = "link_nonce_invalid"
```

## 📦 Step 3: Install Account Linking Routes

```powershell
# Copy the account linking router
Copy-Item account_linking_routes.py app/api/routers/accounts.py
```

## 📦 Step 4: Add Routes to main.py

Open `app/api/main.py` and add:

```python
from app.api.routers.accounts import router as accounts_router

# After other routers
app.include_router(accounts_router)
```

## 📦 Step 5: Add Accounts Page

```powershell
# Create static directory if it doesn't exist
New-Item -ItemType Directory -Force -Path app/web/static

# Copy accounts page
Copy-Item accounts.html app/web/static/accounts.html
```

## 📦 Step 6: Serve Static Files

Add to `app/api/main.py`:

```python
from fastapi.staticfiles import StaticFiles

# After app creation
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
```

## 📦 Step 7: Configure Microsoft OAuth (Optional)

If you want to test Microsoft OAuth, add to `.env`:

```bash
# Microsoft OAuth (Optional - for testing account linking)
MICROSOFT_CLIENT_ID=your_microsoft_app_id
MICROSOFT_CLIENT_SECRET=your_microsoft_secret
```

To get Microsoft credentials:
1. Go to https://portal.azure.com
2. Azure Active Directory → App registrations → New registration
3. Set redirect URI: http://localhost:8000/auth/accounts/callback/microsoft
4. Certificates & secrets → New client secret
5. Add Client ID and Secret to .env

## 🚀 Step 8: Restart Server

```powershell
# Clear cache
Get-ChildItem -Path app -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force

# Restart
.\run.ps1
```

---

## 🧪 Testing Stage 6

### Test 1: View Linked Accounts

**Browser console:**
```javascript
fetch('/auth/accounts').then(r => r.json()).then(console.log);
```

**Expected:**
```json
{
  "user_id": "...",
  "identities": [
    {
      "identity_id": "...",
      "provider_id": "google",
      "provider_email": "your@email.com",
      "email_verified": true,
      "linked_at": "2025-12-25T...",
      "last_used": "2025-12-25T..."
    }
  ],
  "count": 1
}
```

### Test 2: View Accounts Page

Navigate to: `http://localhost:8000/static/accounts.html`

Should show:
- Your current Google account
- Buttons to link Google/Microsoft
- Unlink button (disabled - can't unlink only account)

### Test 3: Link Second Provider

**Option A: Link another Google account**
1. Click "Link Google Account"
2. Choose a different Google account
3. Should redirect back with success message
4. Should see both accounts listed

**Option B: Link Microsoft (if configured)**
1. Add Microsoft credentials to .env
2. Restart server
3. Click "Link Microsoft Account"
4. Login with Microsoft
5. Should see both Google and Microsoft linked

### Test 4: Unlink Provider

Once you have 2+ providers linked:

```javascript
// Get CSRF token
const csrf = document.cookie.split('csrf=')[1]?.split(';')[0];

// Unlink a provider
fetch('/auth/accounts/google', {
  method: 'DELETE',
  headers: {
    'X-CSRF-Token': csrf
  }
}).then(r => r.json()).then(console.log);
```

**Expected:**
```json
{
  "status": "unlinked",
  "provider_id": "google"
}
```

### Test 5: Try to Unlink Last Provider (Should Fail)

```javascript
// If you only have 1 provider, try to unlink it
fetch('/auth/accounts/google', {
  method: 'DELETE',
  headers: {
    'X-CSRF-Token': csrf
  }
}).then(r => r.json()).then(console.log);
```

**Expected 403 Error:**
```json
{
  "detail": "Cannot unlink your only login method. Please link another account first."
}
```

### Test 6: Security Test - Try to Link Already-Linked Identity

1. Link Google account A to User 1
2. Logout, create User 2 with different email
3. Try to link Google account A to User 2

**Expected 403:**
```json
{
  "detail": "This google account is already linked to another user. Please use a different account."
}
```

---

## 📊 Database Verification

```sql
-- View all linked identities
SELECT 
    u.email,
    o.provider_id,
    o.provider_email,
    o.identity_created_at
FROM users u
JOIN user_oauth_identities o ON u.user_id = o.user_id
ORDER BY u.email, o.identity_created_at;

-- View link audit events
SELECT 
    event_type,
    provider_id,
    created_at,
    metadata
FROM auth_audit_log
WHERE event_type IN ('account_linked', 'account_unlinked', 'link_blocked_identity_exists')
ORDER BY created_at DESC
LIMIT 10;

-- View active link nonces (should be empty after successful link)
SELECT * FROM link_intent_nonces WHERE expires_at > NOW();
```

---

## ✅ Success Criteria

- [ ] Can view linked accounts via API
- [ ] Can view accounts page at /static/accounts.html
- [ ] Can link Google account (shows in list)
- [ ] Can link Microsoft account (if configured)
- [ ] Cannot unlink last provider (403 error)
- [ ] Can unlink provider when 2+ linked (success)
- [ ] Cannot link identity already linked to another user (403)
- [ ] Link audit events logged correctly

---

## 🎯 What You've Built

**Complete Multi-Provider OAuth System:**
- ✅ Google OAuth login/logout
- ✅ Microsoft OAuth support
- ✅ Account linking (multiple providers per user)
- ✅ Account unlinking (with safety checks)
- ✅ Link intent nonces (15min expiry, single-use)
- ✅ Security: Prevents unauthorized linking
- ✅ Audit logging for all link/unlink events
- ✅ Simple accounts management UI

**This is production-ready enterprise authentication!** 🏆
