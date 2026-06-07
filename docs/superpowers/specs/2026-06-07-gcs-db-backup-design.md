# GCS Database Backup — Design Spec

**Date:** 2026-06-07  
**Branch:** feature/save_db  
**Status:** Approved

## Problem

The SQLite database (`drift.db`) lives on the GCE instance's local disk. If the instance is wiped or recreated, all memos are lost.

## Goal

Back up `drift.db` to Google Cloud Storage every 6 hours. Single overwriting copy. Zero cost under free tier.

## Constraints

- GCS free tier: us-west1 region, 5 GB storage, 5,000 Class A ops/month
- No changes to the Python bot
- Backup must be safe against corruption during active writes
- Restore must be a single command

## Architecture

```
GCE instance (cron, every 6h)
  └─ deploy/backup.sh
       ├─ sqlite3 $DB_PATH ".backup /tmp/drift_backup.db"   # safe online snapshot
       ├─ gsutil cp /tmp/drift_backup.db gs://$GCS_BUCKET/drift.db
       └─ rm /tmp/drift_backup.db

GCS bucket: gs://drift-db-<project-id>/  (us-west1)
  └─ drift.db   # overwritten each run
```

## Free Tier Impact

| Metric | Usage | Limit |
|---|---|---|
| Storage | < 1 MB | 5 GB/month |
| Class A ops (writes) | ~120/month (4/day × 30) | 5,000/month |
| Egress (restore only) | negligible | 100 GB/month |

## Files

| File | Action | Purpose |
|---|---|---|
| `deploy/backup.sh` | New | Safe snapshot + gsutil upload |
| `deploy/restore.sh` | New | Download from GCS to `$DB_PATH` |
| `deploy/setup.sh` | Update | Install cron entry on the instance |
| `.env.example` | Update | Document `GCS_BUCKET` variable |

## One-Time Manual Setup (operator runs once)

```bash
# Create bucket in us-west1 (free tier region, nearest to Japan)
gsutil mb -l us-west1 gs://drift-db-<your-project-id>/

# Grant GCE default service account write access scoped to the bucket
gsutil iam ch serviceAccount:<sa-email>:roles/storage.objectAdmin gs://drift-db-<your-project-id>/

# Add to .env on the instance
echo "GCS_BUCKET=drift-db-<your-project-id>" >> /opt/memo_cho_bot/.env
```

## Cron Entry (installed by setup.sh)

```
0 */6 * * * /opt/memo_cho_bot/deploy/backup.sh >> /var/log/drift-backup.log 2>&1
```

## Restore Procedure

When rebuilding the instance, after cloning the repo and setting up `.env`:

```bash
bash /opt/memo_cho_bot/deploy/restore.sh
```

This fetches `gs://$GCS_BUCKET/drift.db` and writes it to `$DB_PATH`.

## Error Handling

- `backup.sh` uses `set -euo pipefail` — any failure exits non-zero and is logged to `/var/log/drift-backup.log`
- `restore.sh` checks `$GCS_BUCKET` is set before running
- Both scripts source `.env` to pick up `DB_PATH` and `GCS_BUCKET`
