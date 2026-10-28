# Phase 1: route reachability

- Time: 2026-10-28 10:46:29
- Base URL: http://127.0.0.1:5000
- Result: 0/9 routes reachable

| Method | Path | Result | Route check | Real call |
|---|---|---|---|---|
| POST | `/v1/search` | FAIL | method not allowed, Allow = None | skipped |
| GET | `/v1/similar/test123` | FAIL | method not allowed, Allow = None | GET -> 200 |
| POST | `/v1/takedown` | FAIL | method not allowed, Allow = None | skipped |
| POST | `/v1/sources/test123/enable` | FAIL | method not allowed, Allow = None | skipped |
| POST | `/v1/index/switch` | FAIL | method not allowed, Allow = None | skipped |
| GET | `/v1/ingest/test123` | FAIL | method not allowed, Allow = None | GET -> 200 |
| POST | `/v1/ingest/test123/run` | FAIL | method not allowed, Allow = None | skipped |
| POST | `/v1/index/reembed` | FAIL | method not allowed, Allow = None | skipped |
| GET | `/metrics` | FAIL | method not allowed, Allow = None | GET -> 200 |

POST routes are only checked with OPTIONS, because a real POST can change data.
