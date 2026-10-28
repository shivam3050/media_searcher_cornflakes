# EVAL_RESULTS

Output of `make eval` (`python eval.py`). Numbers we are not happy with are kept on purpose.

- Run at: 2026-10-28 06:31:28 UTC
- Git commit: 74ea69e
- Server: http://localhost:5000

## Summary

| # | Scenario | Result | Finding |
|---|---|---|---|
| T1 | kill -9 the ingest mid-batch | **ERROR** | UndefinedTable: relation "records" does not exist
LINE 1: DELETE FROM records WHERE source = 'met-museum'
                    ^
 |
| T3 | unknown licence never appears | **ERROR** | UndefinedTable: relation "records" does not exist
LINE 1: SELECT r.id::text, r.title, r.caption FROM records r
                                                   ^
 |
| T4 | version mismatch is refused loudly | **ERROR** | UndefinedTable: relation "index_state" does not exist
LINE 1: SELECT live_version FROM index_state LIMIT 1
                                 ^
 |
| T6 | takedown disappears from cached pages within 1 s | **ERROR** | UndefinedTable: relation "records" does not exist
LINE 1: SELECT r.id::text, r.title, r.caption FROM records r
                                                   ^
 |
| T9 | paging is stable while 500 rows are ingested | **ERROR** | UndefinedTable: relation "index_state" does not exist
LINE 1: SELECT live_version FROM index_state LIMIT 1
                                 ^
 |
| T12 | huge and injection-style queries | **FAIL** | 10,000 characters: HTTP 500; 10,000 characters: took 2.06s; sql injection: HTTP 500; sql injection: took 2.05s; boolean injection: HTTP 500; boolean injection: took 2.05s; null bytes and unicode: HTTP 500; null bytes and unicode: took 2.04s; records table is gone |

## Numbers we are not happy with

- **T1 (ERROR)**: UndefinedTable: relation "records" does not exist
LINE 1: DELETE FROM records WHERE source = 'met-museum'
                    ^

- **T3 (ERROR)**: UndefinedTable: relation "records" does not exist
LINE 1: SELECT r.id::text, r.title, r.caption FROM records r
                                                   ^

- **T4 (ERROR)**: UndefinedTable: relation "index_state" does not exist
LINE 1: SELECT live_version FROM index_state LIMIT 1
                                 ^

- **T6 (ERROR)**: UndefinedTable: relation "records" does not exist
LINE 1: SELECT r.id::text, r.title, r.caption FROM records r
                                                   ^

- **T9 (ERROR)**: UndefinedTable: relation "index_state" does not exist
LINE 1: SELECT live_version FROM index_state LIMIT 1
                                 ^

- **T12 (FAIL)**: 10,000 characters: HTTP 500; 10,000 characters: took 2.06s; sql injection: HTTP 500; sql injection: took 2.05s; boolean injection: HTTP 500; boolean injection: took 2.05s; null bytes and unicode: HTTP 500; null bytes and unicode: took 2.04s; records table is gone

## Details

### T1 - kill -9 the ingest mid-batch

Result: **ERROR** (2.1s)

UndefinedTable: relation "records" does not exist
LINE 1: DELETE FROM records WHERE source = 'met-museum'
                    ^


- note: Traceback (most recent call last):
  File "d:\myCodings\2024\garbage\learningWEB\js_cheat_part_code\media_searcher_cornflakes\eval2.py", line 535, in main
    res = fn()
          ^^^^
  File "d:\myCodings\2024\garbage\learningWEB\js_cheat_part_code\media_searcher_cornflakes\eval2.py", line 177, in t1_kill_ingest
    sql("DELETE FROM records WHERE source = %s", (slug,))
  File "d:\myCodings\2024\garbage\learningWEB\js_cheat_part_code\media_searcher_cornflakes\eval2.py", line 70, in sql
    cur.execute(query, params)
psycopg2.errors.UndefinedTable: relation "records" does not exist
LINE 1: DELETE FROM records WHERE source = 'met-museum'
                    ^



### T3 - unknown licence never appears

Result: **ERROR** (0.0s)

UndefinedTable: relation "records" does not exist
LINE 1: SELECT r.id::text, r.title, r.caption FROM records r
                                                   ^


- note: Traceback (most recent call last):
  File "d:\myCodings\2024\garbage\learningWEB\js_cheat_part_code\media_searcher_cornflakes\eval2.py", line 535, in main
    res = fn()
          ^^^^
  File "d:\myCodings\2024\garbage\learningWEB\js_cheat_part_code\media_searcher_cornflakes\eval2.py", line 254, in t3_unknown_licence
    rows = sql("""SELECT r.id::text, r.title, r.caption FROM records r
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "d:\myCodings\2024\garbage\learningWEB\js_cheat_part_code\media_searcher_cornflakes\eval2.py", line 70, in sql
    cur.execute(query, params)
psycopg2.errors.UndefinedTable: relation "records" does not exist
LINE 1: SELECT r.id::text, r.title, r.caption FROM records r
                                                   ^



### T4 - version mismatch is refused loudly

Result: **ERROR** (2.1s)

UndefinedTable: relation "index_state" does not exist
LINE 1: SELECT live_version FROM index_state LIMIT 1
                                 ^


- note: Traceback (most recent call last):
  File "d:\myCodings\2024\garbage\learningWEB\js_cheat_part_code\media_searcher_cornflakes\eval2.py", line 535, in main
    res = fn()
          ^^^^
  File "d:\myCodings\2024\garbage\learningWEB\js_cheat_part_code\media_searcher_cornflakes\eval2.py", line 285, in t4_version_mismatch
    original = sql("SELECT live_version FROM index_state LIMIT 1")[0][0]
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "d:\myCodings\2024\garbage\learningWEB\js_cheat_part_code\media_searcher_cornflakes\eval2.py", line 70, in sql
    cur.execute(query, params)
psycopg2.errors.UndefinedTable: relation "index_state" does not exist
LINE 1: SELECT live_version FROM index_state LIMIT 1
                                 ^



### T6 - takedown disappears from cached pages within 1 s

Result: **ERROR** (2.1s)

UndefinedTable: relation "records" does not exist
LINE 1: SELECT r.id::text, r.title, r.caption FROM records r
                                                   ^


- note: Traceback (most recent call last):
  File "d:\myCodings\2024\garbage\learningWEB\js_cheat_part_code\media_searcher_cornflakes\eval2.py", line 535, in main
    res = fn()
          ^^^^
  File "d:\myCodings\2024\garbage\learningWEB\js_cheat_part_code\media_searcher_cornflakes\eval2.py", line 310, in t6_takedown_cached_pages
    cands = sql("""SELECT r.id::text, r.title, r.caption FROM records r
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "d:\myCodings\2024\garbage\learningWEB\js_cheat_part_code\media_searcher_cornflakes\eval2.py", line 70, in sql
    cur.execute(query, params)
psycopg2.errors.UndefinedTable: relation "records" does not exist
LINE 1: SELECT r.id::text, r.title, r.caption FROM records r
                                                   ^



### T9 - paging is stable while 500 rows are ingested

Result: **ERROR** (0.0s)

UndefinedTable: relation "index_state" does not exist
LINE 1: SELECT live_version FROM index_state LIMIT 1
                                 ^


- note: Traceback (most recent call last):
  File "d:\myCodings\2024\garbage\learningWEB\js_cheat_part_code\media_searcher_cornflakes\eval2.py", line 535, in main
    res = fn()
          ^^^^
  File "d:\myCodings\2024\garbage\learningWEB\js_cheat_part_code\media_searcher_cornflakes\eval2.py", line 365, in t9_paging_during_ingest
    live = sql("SELECT live_version FROM index_state LIMIT 1")[0][0]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "d:\myCodings\2024\garbage\learningWEB\js_cheat_part_code\media_searcher_cornflakes\eval2.py", line 70, in sql
    cur.execute(query, params)
psycopg2.errors.UndefinedTable: relation "index_state" does not exist
LINE 1: SELECT live_version FROM index_state LIMIT 1
                                 ^



### T12 - huge and injection-style queries

Result: **FAIL** (8.3s)

10,000 characters: HTTP 500; 10,000 characters: took 2.06s; sql injection: HTTP 500; sql injection: took 2.05s; boolean injection: HTTP 500; boolean injection: took 2.05s; null bytes and unicode: HTTP 500; null bytes and unicode: took 2.04s; records table is gone

- 10,000 characters: http / seconds: `500 / 2.060`
- sql injection: http / seconds: `500 / 2.054`
- boolean injection: http / seconds: `500 / 2.046`
- null bytes and unicode: http / seconds: `500 / 2.043`
- records table still exists: `False`
