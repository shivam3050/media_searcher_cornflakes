# Architecture

## Overview

Every request or command first reaches the **Server**. The server **verifies** it and decides whether it is a **public request** or an **admin command**. Each type is handled by a different worker, so heavy admin work never slows down public search.

## Request flow

1. A request or command arrives at the **Server**.
2. The server **verifies** it (public user or admin).
3. It goes down one of three paths:

| Path | Handled by | What happens |
|---|---|---|
| Public request | public worker | The request is processed (search, similar). |
| Admin command, heavy | private heavy worker | `run` starts the job, which processes records into PostgreSQL. |
| Admin command, simple | private simple worker | The command is processed (takedown, source on/off, index switch). |

## Components

- **Server**: the single entry point. Verifies each request and routes it.
- **Public worker**: serves public requests only.
- **Private heavy worker**: runs ingest and re-embed. These are slow and CPU heavy.
- **Private simple worker**: runs small admin commands that only read or write a little data.
- **media Locations** (`public-mock-internet/`): the mock sources the heavy worker reads from.
- **PostgreSQL**: the single place where all data is stored.

## Heavy path (ingest)

```
admin command -> private heavy worker -> run
  -> async / await -> process to PostgreSQL <- media Locations
  -> PostgreSQL
```

The heavy worker reads records from the media locations, processes each one, and saves it to PostgreSQL. The server only queues the job in the `jobs` table; the worker picks it up.

## Mock sources (`public-mock-internet/`)

What comes from the mock internet is **raw JSON data**. Each record has the fields `source, source_ref, title, caption?, tags[], year, license, nsfw_score, visual_vec[64], phash`. The image is already represented by `visual_vec` and `phash`. `caption` is optional; when it is missing, the mock captioner llm builds one from the tags.

| Source | Format | Notes |
|---|---|---|
| `met-museum/` | `records.jsonl` | JSONL file adapter. |
| `flickr/` | `pages/page_1.json` ... `page_6.json` | Paginated adapter with `next_cursor`. The mock server adds random 429 / 5xx. |
| `unsplash/` | `records.jsonl`, `robots.txt` | A `Disallow: /` robots file must quarantine the source. |
| `user-uploads/` | `records.jsonl`, `records_update.jsonl` | Test cases: unknown licence, high NSFW score, near-duplicates, changed records. |

## Database tables

| Table | Purpose |
|---|---|
| `sources` | One row per source: status (enabled, disabled, quarantined) and ingest cursor. |
| `records` | One row per image: metadata, licence, NSFW score, thumbnail, `text_vec` + `text_ver`, `visual_vec` + `visual_ver`. |
| `jobs` | Queue between the server and the heavy worker: type, source, status, progress, error. |
| `index_state` | One row: the live embedding version and the cache version. |
| `audit_log` | Append-only log of takedowns. |

## Key rules

- Writes to `records` are upserts on `(source, source_ref)`, so re-running an ingest never creates duplicates.
- The cursor is saved only after a batch is committed.
- Every vector is stored with its version (`text_ver`, `visual_ver`). Vectors from different versions are never compared.
- Records with an unknown licence are never indexed.
- Full-size images are never stored, only thumbnails.

## Files

| Part | File |
|---|---|
| Entry point | `backend/server.py` |
| Routes | `backend/routes/routes.py` |
| Database connection | `backend/utilities/db.py` |
| Create tables | `backend/utilities/init_db.py` |
| Table definitions | `backend/models/schema.sql` |
| Public / simple admin work | `backend/utilities/general_worker.py` |
| Heavy work (ingest, re-embed) | `backend/utilities/heavy_worker.py` |
| Mock record's attributes rewriter | `backend/utilities/llm.py` |