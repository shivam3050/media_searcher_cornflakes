# Phase 2: POST /v1/search

- Time: 2026-10-28 10:46:30
- Base URL: http://127.0.0.1:5000
- PASS: 16, FAIL: 2, SKIP: 4

| Test | Result | Note |
|---|---|---|
| 1. search returns 200 and JSON | PASS | status 200 |
| 2. reply has results, next_cursor, index_version, cached | PASS | all keys present |
| 3. each result has id, score, caption_rank, visual_rank | SKIP | no results, is data ingested? |
| 4. k=3 gives at most 3 results | SKIP | no results, is data ingested? |
| 5. results are sorted by score (high to low) | SKIP | less than 2 results |
| 6. same query again has cached = true | FAIL | cached = False |
| 7. cached results are same as first | PASS | same ids, same order |
| 8. index_version is same in both calls | PASS | index_version = v1 |
| 9. '  PORTRAIT  ' shares cache with 'portrait' | FAIL | cached = False |
| 10. page 2 has no duplicates of page 1 | SKIP | next_cursor is empty, need more data |
| 11a. source = no-such-source gives 0 results | PASS | 0 results |
| 11b. license = no-such-license gives 0 results | PASS | 0 results |
| 11c. year_min = 9999 gives 0 results | PASS | 0 results |
| 12a. empty q does not crash | PASS | status 200 |
| 12b. q missing does not crash | PASS | status 200 |
| 12c. k = 0 does not crash | PASS | status 200 |
| 12d. k = -1 does not crash | PASS | status 200 |
| 12e. k = 'abc' does not crash | PASS | status 200 |
| 12f. filters is a string does not crash | PASS | status 200 |
| 12g. wrong cursor does not crash | PASS | status 200 |
| 13. 10000 character query | PASS | status 200, 0.02 sec |
| 14. injection style query | PASS | status 200 |

SKIP means the test could not run (for example no data ingested yet).
