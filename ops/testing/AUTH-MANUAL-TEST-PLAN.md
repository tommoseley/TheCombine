# The Combine - Authentication Manual Test Plan

**Version:** 1.3  
**Last Updated:** 2026-01-07  
**Author:** Tom Moseley

---

## Overview

This document provides step-by-step instructions for manually testing all authentication flows in The Combine. Run through this checklist after any changes to authentication code, OAuth configuration, or deployment infrastructure.

---

## Environment Configuration

| Environment | Base URL | Database Host |
|-------------|----------|---------------|
| **Dev** | http://localhost:8000 | localhost |
| **Prod** | https://www.thecombine.ai | the-combine-db.cyqzjxl9c9jd.us-east-1.rds.amazonaws.com |

**Testing Date:** _______________  
**Environment:** [ ] Dev  [ ] Prod  
**Tester:** _______________

---

## Phase 0: Prerequisites & Cleanup

### 0.1 Verify Application Running
- [ ] Open `{BASE_URL}/health` in browser
- [ ] Confirm response: `{"status":"healthy"}`

### 0.2 Database Cleanup (Optional - for clean slate testing)

**WARNING: This deletes all user data!**

```sql
DELETE FROM auth_audit_log;
DELETE FROM link_intent_nonces;
DELETE FROM user_sessions;
DELETE FROM user_oauth_identities;
DELETE FROM users;
```

---

## Phase 1-11: See full test plan

(Phases 1-11 cover Google OAuth, Session Persistence, Logout, Returning User, Account Linking, Login with Linked Account, Account Unlinking, Email Match Auto-Link, Microsoft Standalone, Error Handling, and Final Database Audit)

---

## Test Summary

| Phase | Description | Result |
|-------|-------------|--------|
| 0 | Prerequisites & Cleanup | |
| 1 | Google OAuth - New User | |
| 2 | Session Persistence | |
| 3 | Logout | |
| 4 | Google OAuth - Returning User | |
| 5 | Account Linking - Add Microsoft | |
| 6 | Login with Linked Account | |
| 7 | Account Unlinking | |
| 8 | Email Match - Auto Link | |
| 9 | Microsoft OAuth - Standalone New User | |
| 10 | Error Handling | |
| 11 | Final Database Audit | |

**Overall Result:** [ ] PASS  [ ] FAIL
