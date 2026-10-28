# EVAL_RESULTS

Output of `make eval` (`python eval.py`). Numbers we are not happy with are kept on purpose.

- Run at: 2026-10-28 09:21:35 UTC
- Git commit: unknown
- Server: http://localhost:5000

## Summary

| # | Scenario | Result | Finding |
|---|---|---|---|
| T1 | kill -9 the ingest mid-batch | **ERROR** | IndexError: list index out of range |
| T3 | unknown licence never appears | **INCONCLUSIVE** | no unknown-licence record in an enabled source; ingest 'user-uploads' first |
| T4 | version mismatch is refused loudly | **ERROR** | UndefinedColumn: column "live_version" does not exist
LINE 1: SELECT live_version FROM index_state LIMIT 1
               ^
HINT:  Perhaps you meant to reference the column "index_state.active_version". |
| T6 | takedown disappears from cached pages within 1 s | **ERROR** | UndefinedColumn: column r.status does not exist
LINE 3: ...        WHERE r.license <> 'unknown' AND COALESCE(r.status, ...
                                                             ^
HINT:  Perhaps you meant to reference the column "so.status". |
| T9 | paging is stable while 500 rows are ingested | **ERROR** | UndefinedColumn: column "live_version" does not exist
LINE 1: SELECT live_version FROM index_state LIMIT 1
               ^
HINT:  Perhaps you meant to reference the column "index_state.active_version". |
| T12 | huge and injection-style queries | **FAIL** | sql injection: HTTP 500; boolean injection: HTTP 500; null bytes and unicode: HTTP 500 |

## Numbers we are not happy with

- **T1 (ERROR)**: IndexError: list index out of range
- **T3 (INCONCLUSIVE)**: no unknown-licence record in an enabled source; ingest 'user-uploads' first
- **T4 (ERROR)**: UndefinedColumn: column "live_version" does not exist
LINE 1: SELECT live_version FROM index_state LIMIT 1
               ^
HINT:  Perhaps you meant to reference the column "index_state.active_version".
- **T6 (ERROR)**: UndefinedColumn: column r.status does not exist
LINE 3: ...        WHERE r.license <> 'unknown' AND COALESCE(r.status, ...
                                                             ^
HINT:  Perhaps you meant to reference the column "so.status".
- **T9 (ERROR)**: UndefinedColumn: column "live_version" does not exist
LINE 1: SELECT live_version FROM index_state LIMIT 1
               ^
HINT:  Perhaps you meant to reference the column "index_state.active_version".
- **T12 (FAIL)**: sql injection: HTTP 500; boolean injection: HTTP 500; null bytes and unicode: HTTP 500

## Details

### T1 - kill -9 the ingest mid-batch

Result: **ERROR** (60.1s)

IndexError: list index out of range

- note: Traceback (most recent call last):
  File "/app/backend/evaluation/eval2.py", line 535, in main
    res = fn()
          ^^^^
  File "/app/backend/evaluation/eval2.py", line 197, in t1_kill_ingest
    cursor_after_kill = sql("SELECT cursor FROM sources WHERE slug = %s", (slug,))[0][0]
                        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^
IndexError: list index out of range


### T3 - unknown licence never appears

Result: **INCONCLUSIVE** (0.0s)

no unknown-licence record in an enabled source; ingest 'user-uploads' first


### T4 - version mismatch is refused loudly

Result: **ERROR** (0.0s)

UndefinedColumn: column "live_version" does not exist
LINE 1: SELECT live_version FROM index_state LIMIT 1
               ^
HINT:  Perhaps you meant to reference the column "index_state.active_version".

- note: Traceback (most recent call last):
  File "/app/backend/evaluation/eval2.py", line 535, in main
    res = fn()
          ^^^^
  File "/app/backend/evaluation/eval2.py", line 285, in t4_version_mismatch
    original = sql("SELECT live_version FROM index_state LIMIT 1")[0][0]
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/backend/evaluation/eval2.py", line 70, in sql
    cur.execute(query, params)
psycopg.errors.UndefinedColumn: column "live_version" does not exist
LINE 1: SELECT live_version FROM index_state LIMIT 1
               ^
HINT:  Perhaps you meant to reference the column "index_state.active_version".


### T6 - takedown disappears from cached pages within 1 s

Result: **ERROR** (0.0s)

UndefinedColumn: column r.status does not exist
LINE 3: ...        WHERE r.license <> 'unknown' AND COALESCE(r.status, ...
                                                             ^
HINT:  Perhaps you meant to reference the column "so.status".

- note: Traceback (most recent call last):
  File "/app/backend/evaluation/eval2.py", line 535, in main
    res = fn()
          ^^^^
  File "/app/backend/evaluation/eval2.py", line 310, in t6_takedown_cached_pages
    cands = sql("""SELECT r.id::text, r.title, r.caption FROM records r
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/backend/evaluation/eval2.py", line 70, in sql
    cur.execute(query, params)
psycopg.errors.UndefinedColumn: column r.status does not exist
LINE 3: ...        WHERE r.license <> 'unknown' AND COALESCE(r.status, ...
                                                             ^
HINT:  Perhaps you meant to reference the column "so.status".


### T9 - paging is stable while 500 rows are ingested

Result: **ERROR** (0.0s)

UndefinedColumn: column "live_version" does not exist
LINE 1: SELECT live_version FROM index_state LIMIT 1
               ^
HINT:  Perhaps you meant to reference the column "index_state.active_version".

- note: Traceback (most recent call last):
  File "/app/backend/evaluation/eval2.py", line 535, in main
    res = fn()
          ^^^^
  File "/app/backend/evaluation/eval2.py", line 365, in t9_paging_during_ingest
    live = sql("SELECT live_version FROM index_state LIMIT 1")[0][0]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/backend/evaluation/eval2.py", line 70, in sql
    cur.execute(query, params)
psycopg.errors.UndefinedColumn: column "live_version" does not exist
LINE 1: SELECT live_version FROM index_state LIMIT 1
               ^
HINT:  Perhaps you meant to reference the column "index_state.active_version".


### T12 - huge and injection-style queries

Result: **FAIL** (0.0s)

sql injection: HTTP 500; boolean injection: HTTP 500; null bytes and unicode: HTTP 500

- 10,000 characters: http / seconds: `422 / 0.006`
- sql injection: http / seconds: `500 / 0.007`
- boolean injection: http / seconds: `500 / 0.006`
- null bytes and unicode: http / seconds: `500 / 0.003`
- records table still exists: `True`
