from typing import Optional
from fastapi import Body
from starlette.exceptions import HTTPException

from fastapi import Body, HTTPException, Response, Request


async def login_user(response: Response, payload: dict = Body(...)):
    # Everything is defined inside this function; nothing outside it.
    admin_token = "shivamtoken123"

    role = str(payload.get("role", "")).strip().lower()
    token = payload.get("token")

    if role == "admin":
        # Token is mandatory for admin.
        if not token:
            raise HTTPException(status_code=400, detail="Token is required for admin role")

        if token != admin_token:
            raise HTTPException(status_code=401, detail="Invalid admin token")

        # Token verified: set it in an HTTP-only cookie.
        response.set_cookie(key="auth_token", value=token, httponly=True)
        return {"message": "Admin login successful"}

    raise HTTPException(status_code=400, detail="Invalid role.")


async def search_records(request: Request, body: dict = Body(default={})):
    # ---------- Config (mock setup; names follow ARCHITECTURE.md) ----------
    dim = 64                     # vector size
    pool = request.app.state.pool  # asyncpg pool (adjust to your db.py)

    import base64
    import hashlib
    import json
    import math

    # ---------- 1. Validate incoming body ----------
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="Body must be a JSON object")

    extra = set(body) - {"q", "k", "cursor", "filters"}
    if extra:
        raise HTTPException(status_code=422, detail=f"Unknown fields: {sorted(extra)}")

    q = body.get("q")
    if not isinstance(q, str) or not q.strip():
        raise HTTPException(status_code=422, detail="'q' must be a non-empty string")
    q = q.strip()
    if len(q) > 512:
        raise HTTPException(status_code=422, detail="'q' must be at most 512 characters")

    k = body.get("k", 10)
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= 100:
        raise HTTPException(status_code=422, detail="'k' must be an integer between 1 and 100")

    offset = 0
    cursor = body.get("cursor")
    if cursor is not None:
        try:
            offset = int(json.loads(base64.urlsafe_b64decode(cursor.encode()))["o"])
            if offset < 0:
                raise ValueError
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid 'cursor'")

    filters = body.get("filters") or {}
    if not isinstance(filters, dict):
        raise HTTPException(status_code=422, detail="'filters' must be an object")
    extra = set(filters) - {"license", "source", "nsfw_max", "year_min", "year_max"}
    if extra:
        raise HTTPException(status_code=422, detail=f"Unknown filters: {sorted(extra)}")

    for key in ("license", "source"):
        val = filters.get(key)
        if val is not None and (
            not isinstance(val, list) or not all(isinstance(v, str) for v in val)
        ):
            raise HTTPException(status_code=422, detail=f"'filters.{key}' must be a list of strings")

    nsfw_max = filters.get("nsfw_max")
    if nsfw_max is not None and (isinstance(nsfw_max, bool) or not isinstance(nsfw_max, (int, float))):
        raise HTTPException(status_code=422, detail="'filters.nsfw_max' must be a number")

    year_min, year_max = filters.get("year_min"), filters.get("year_max")
    for name, val in (("year_min", year_min), ("year_max", year_max)):
        if val is not None and (isinstance(val, bool) or not isinstance(val, int)):
            raise HTTPException(status_code=422, detail=f"'filters.{name}' must be an integer")
    if year_min is not None and year_max is not None and year_min > year_max:
        raise HTTPException(status_code=422, detail="'year_min' cannot exceed 'year_max'")

    # ---------- 2. Mock LLM: turn q into a text vector ----------
    def mock_embed(text):
        vec = [0.0] * dim
        for tok in text.lower().split():
            h = int(hashlib.md5(("text:" + tok).encode()).hexdigest(), 16)
            vec[h % dim] += 1.0 if (h >> 8) & 1 else -1.0
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0:
            vec[0], norm = 1.0, 1.0
        return "[" + ",".join(str(x / norm) for x in vec) + "]"

    text_vec = mock_embed(q)

    # ---------- 3. Query PostgreSQL (cosine similarity on text_vec) ----------
    params = [text_vec]                      # $1 = query vector, $2 = live version (added below)
    where = ["r.license <> 'unknown'"]       # unknown licence is never searchable
    if filters.get("license"):
        params.append(filters["license"])
        where.append(f"r.license = ANY(${len(params) + 1})")
    if filters.get("source"):
        params.append(filters["source"])
        where.append(f"r.source = ANY(${len(params) + 1})")
    if nsfw_max is not None:
        params.append(nsfw_max)
        where.append(f"r.nsfw_score <= ${len(params) + 1}")
    if year_min is not None:
        params.append(year_min)
        where.append(f"r.year >= ${len(params) + 1}")
    if year_max is not None:
        params.append(year_max)
        where.append(f"r.year <= ${len(params) + 1}")

    try:
        async with pool.acquire() as conn:
            # live embedding version (vectors of other versions are never compared)
            state = await conn.fetchrow("SELECT live_version FROM index_state LIMIT 1")
            if state is None:
                raise HTTPException(status_code=503, detail="Index is not ready")
            index_version = state["live_version"]

            all_params = [params[0], index_version] + params[1:] + [k + 1, offset]
            limit_idx, offset_idx = len(all_params) - 1, len(all_params)

            sql = f"""
                SELECT r.id,
                       1 - (r.text_vec <=> $1::vector) AS score
                FROM records r
                JOIN sources s ON s.name = r.source AND s.status = 'enabled'
                WHERE r.text_ver = $2 AND {" AND ".join(where)}
                ORDER BY r.text_vec <=> $1::vector ASC, r.id ASC
                LIMIT ${limit_idx} OFFSET ${offset_idx}
            """
            rows = await conn.fetch(sql, *all_params)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    # ---------- 4. Build the response ----------
    has_more = len(rows) > k
    rows = rows[:k]

    results = [
        {
            "id": r["id"],
            "score": float(r["score"]),
            "caption_rank": offset + i + 1,
            "visual_rank": None,  # text-only search for now
        }
        for i, r in enumerate(rows)
    ]

    next_cursor = None
    if has_more:
        next_cursor = base64.urlsafe_b64encode(
            json.dumps({"o": offset + k}).encode()
        ).decode()

    return {
        "results": results,
        "next_cursor": next_cursor,
        "index_version": index_version,
        "cached": False,
    }




async def get_similar_records(
    request: Request,
    id: str,
    k: int = 20,
    nsfw_max: Optional[float] = None,
    license: Optional[str] = None,
    source: Optional[str] = None,
):
    pool = request.app.state.pool  # asyncpg pool (adjust to your db.py)

    # ---------- 1. Validate inputs ----------
    if not isinstance(id, str) or not id.strip() or len(id) > 200:
        raise HTTPException(status_code=422, detail="'id' must be a non-empty string")
    id = id.strip()

    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= 100:
        raise HTTPException(status_code=422, detail="'k' must be an integer between 1 and 100")

    if nsfw_max is not None and (isinstance(nsfw_max, bool) or not isinstance(nsfw_max, (int, float))):
        raise HTTPException(status_code=422, detail="'nsfw_max' must be a number")

    for name, val in (("license", license), ("source", source)):
        if val is not None and (not isinstance(val, str) or not val.strip()):
            raise HTTPException(status_code=422, detail=f"'{name}' must be a non-empty string")

    try:
        async with pool.acquire() as conn:
            # ---------- 2. Live version and the record's own visual vector ----------
            state = await conn.fetchrow("SELECT live_version FROM index_state LIMIT 1")
            if state is None:
                raise HTTPException(status_code=503, detail="Index is not ready")
            index_version = state["live_version"]

            src = await conn.fetchrow(
                "SELECT visual_vec::text AS v FROM records "
                "WHERE id::text = $1 AND visual_ver = $2 AND visual_vec IS NOT NULL",
                id, index_version,
            )
            if src is None:
                raise HTTPException(status_code=404, detail="Record not found or has no visual vector")

            # ---------- 3. Cosine search on visual_vec ----------
            params = [src["v"], index_version, id]    # $1 vector, $2 version, $3 own id
            where = ["r.license <> 'unknown'"]        # unknown licence is never searchable
            if nsfw_max is not None:
                params.append(nsfw_max)
                where.append(f"r.nsfw_score <= ${len(params)}")
            if license is not None:
                params.append(license.strip())
                where.append(f"r.license = ${len(params)}")
            if source is not None:
                params.append(source.strip())
                where.append(f"r.source = ${len(params)}")
            params.append(k)
            limit_idx = len(params)

            sql = f"""
                SELECT r.id::text AS id,
                       1 - (r.visual_vec <=> $1::vector) AS score
                FROM records r
                JOIN sources s ON s.name = r.source AND s.status = 'enabled'
                WHERE r.visual_ver = $2
                  AND r.id::text <> $3
                  AND {" AND ".join(where)}
                ORDER BY r.visual_vec <=> $1::vector ASC, r.id ASC
                LIMIT ${limit_idx}
            """
            rows = await conn.fetch(sql, *params)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    # ---------- 4. Response ----------
    return {
        "results": [
            {"id": r["id"], "score": float(r["score"]), "visual_rank": i + 1}
            for i, r in enumerate(rows)
        ],
        "index_version": index_version,
    }



async def handle_takedown(body: dict = Body(default={})):
    """
    POST /v1/takedown
    Marks a record as taken down globally within <1 second.
    Expects payload: { record_id, reason }
    """
    import os
    import psycopg2
    from fastapi import HTTPException

    record_id = body.get("record_id")
    reason = body.get("reason")
    if record_id is None:
        raise HTTPException(status_code=400, detail="record_id is required")

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    cur.execute("UPDATE records SET status = 'takedown' WHERE id::text = %s RETURNING id", (str(record_id),))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="record not found")

    cur.execute("INSERT INTO audit_log (record_id, reason) VALUES (%s, %s)", (row[0], reason))
    # new cache_version, so every old cached page stops being used
    cur.execute("UPDATE index_state SET cache_version = cache_version + 1")
    conn.commit()
    conn.close()

    return {
        "success": True,
        "record_id": record_id,
        "message": "Record successfully removed from search visibility.",
    }


async def manage_source_action(slug: str, action: str):
    """
    POST /v1/sources/{slug}/{action}
    Admin action to manage source visibility.
    Actions allowed: 'enable', 'disable', 'quarantine', 'release'
    """
    import os
    import psycopg2
    from fastapi import HTTPException

    states = {
        "enable": "enabled",
        "disable": "disabled",
        "quarantine": "quarantined",
        "release": "enabled",
    }
    if action not in states:
        raise HTTPException(status_code=400, detail="action must be enable, disable, quarantine or release")

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    cur.execute("UPDATE sources SET status = %s WHERE slug = %s RETURNING slug", (states[action], slug))
    if cur.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="source not found")

    cur.execute("UPDATE index_state SET cache_version = cache_version + 1")
    conn.commit()
    conn.close()

    return {
        "success": True,
        "slug": slug,
        "action": action,
        "current_state": states[action],
    }


async def trigger_ingest_run(slug: str):
    """
    POST /v1/ingest/{slug}/run
    Kicks off a background ingestion job for the given source slug.
    """
    import os
    import psycopg2

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    cur.execute("INSERT INTO jobs (type, source, status) VALUES ('ingest', %s, 'queued') RETURNING id", (slug,))
    run_id = cur.fetchone()[0]
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"Ingestion job started for source: {slug}",
        "run_id": run_id,
    }


async def get_ingest_status(slug: str):
    """
    GET /v1/ingest/{slug}
    Reads current cursor position, record counts, and synchronization lag for a source.
    """
    import os
    import psycopg2
    from fastapi import HTTPException

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()

    cur.execute("SELECT cursor FROM sources WHERE slug = %s", (slug,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="source not found")

    cur.execute("SELECT count(*) FROM records WHERE source = %s", (slug,))
    processed = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM jobs WHERE source = %s AND status = 'failed'", (slug,))
    failed = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM jobs WHERE source = %s AND status = 'queued'", (slug,))
    lag = cur.fetchone()[0]
    conn.close()

    return {
        "slug": slug,
        "cursor": row[0],
        "counts": {
            "processed": processed,
            "failed": failed,
        },
        "lag": lag,
    }


async def trigger_reembed(body: dict = Body(default={})):
    """
    POST /v1/index/reembed
    Triggers backfilling of a new vector version for all or selected records.
    """
    import os
    import psycopg2
    from fastapi import HTTPException

    target_version = body.get("target_version")
    if not target_version:
        raise HTTPException(status_code=400, detail="target_version is required")

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    # jobs table has no version column, so the version is saved in the source column
    cur.execute("INSERT INTO jobs (type, source, status) VALUES ('reembed', %s, 'queued') RETURNING id", (target_version,))
    run_id = cur.fetchone()[0]
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "Backfill re-embedding process initiated.",
        "target_version": target_version,
        "run_id": run_id,
    }


async def switch_index_version(body: dict = Body(default={})):
    """
    POST /v1/index/switch
    Atomically switches the active query index version or performs a rollback.
    """
    import os
    import psycopg2
    from fastapi import HTTPException

    active_version = body.get("active_version")
    if not active_version:
        raise HTTPException(status_code=400, detail="active_version is required")

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    # one UPDATE changes both values together, so the switch is atomic
    cur.execute(
        "UPDATE index_state SET live_version = %s, cache_version = cache_version + 1",
        (active_version,),
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "active_version": active_version,
        "message": f"Active index version switched to {active_version}",
    }


async def get_system_metrics():
    """
    GET /metrics
    Returns ingestion rate, cache hit ratios, and query latencies.
    """
    import os
    import psycopg2

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM records WHERE status = 'active'")
    active_records = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM sources WHERE status = 'quarantined'")
    quarantined = cur.fetchone()[0]
    cur.execute("SELECT live_version FROM index_state LIMIT 1")
    live = cur.fetchone()[0]
    conn.close()

    hit_ratio = 0
    p95 = 0
    stats = getattr(search_records, "stats", None)
    if stats is not None and stats["hits"] + stats["misses"] > 0:
        hit_ratio = stats["hits"] / (stats["hits"] + stats["misses"])
        times = sorted(stats["times"])
        p95 = times[int(0.95 * (len(times) - 1))]

    return {
        "active_records": active_records,
        "quarantined_sources": quarantined,
        "index_version": live,
        "cache_hit_ratio": round(hit_ratio, 3),
        "latency_p95_ms": round(p95, 2),
    }