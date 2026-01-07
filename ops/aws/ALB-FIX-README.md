# ALB Fix Scripts

These scripts fix the ECS service to use the Application Load Balancer.

## Problem
1. The ECS service was created without a load balancer attached (`"loadBalancers": []`)
2. The deploy.yml was updating Route 53 directly to point to task IPs on each deploy
3. Fragment markup in DB uses CSS classes instead of Tailwind (blank Open Questions)

## Solution
1. Recreate ECS service with ALB target group attached
2. Update task definition for ALB (DOMAIN, HTTPS_ONLY)
3. Update deploy.yml to work with ALB (no Route 53 updates)
4. Update fragment markup in production database

## Scripts (run in order)

### Step 1: Delete existing service
```powershell
.\alb-fix-01-delete-service.ps1
```
Wait 1-2 minutes for deletion to complete.

### Step 2: Create service with ALB
```powershell
.\alb-fix-02-create-service.ps1
```
Wait 2-3 minutes for task to start and register with ALB.

### Step 3: Update task definition
```powershell
.\alb-fix-03-update-task-def.ps1
```
This updates DOMAIN and HTTPS_ONLY for proper ALB operation.

### Step 4: Update fragment markup in database
```powershell
.\alb-fix-04-update-fragment-db.ps1
```
Shows instructions for running the SQL update.

SQL file: `update-fragment-markup.sql`

## Verify
```bash
curl -I https://thecombine.ai
```
Should return HTTP 200.

## Also Updated
- `.github/workflows/deploy.yml` - Removed Route 53 updates, simplified for ALB