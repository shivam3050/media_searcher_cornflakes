# Phase 1: route reachability

- Time: 2026-10-28 15:01:27
- Base URL: http://localhost:5000
- Result: 9/9 routes reachable

| Method | Path | Result | Route check | Real call |
|---|---|---|---|---|
| POST | `/v1/search` | PASS | 405, Allow = POST | skipped |
| GET | `/v1/similar/test123` | PASS | 405, Allow = GET | GET -> 500 |
| POST | `/v1/takedown` | PASS | 405, Allow = POST | skipped |
| POST | `/v1/sources/test123/enable` | PASS | 405, Allow = POST | skipped |
| POST | `/v1/index/switch` | PASS | 405, Allow = POST | skipped |
| GET | `/v1/ingest/test123` | PASS | 405, Allow = GET | GET -> 500 |
| POST | `/v1/ingest/test123/run` | PASS | 405, Allow = POST | skipped |
| POST | `/v1/index/reembed` | PASS | 405, Allow = POST | skipped |
| GET | `/metrics` | PASS | 405, Allow = GET | GET -> 500 |

POST routes are only checked with OPTIONS, because a real POST can change data.
