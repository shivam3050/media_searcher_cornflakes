#!/usr/bin/env python3
"""
eval.py - automated checks for the "Traps We Will Test" (T1, T3, T4, T6, T9, T12).

Run with:        python eval.py            (or: make eval)
Run a subset:    python eval.py --only T3,T6
Output:          EVAL_RESULTS.md (overwritten on every run; commit it, bad numbers included)

Requirements:    pip install requests psycopg2-binary psutil python-dotenv
The backend server and the heavy worker must already be running against a
DEVELOPMENT database: T1 and T9 write to, and delete from, the records table.

Configuration (environment variables, all optional except DATABASE_URL):
    DATABASE_URL            postgres connection string (also read from backend/.env)
    EVAL_BASE_URL           default http://localhost:8000
    EVAL_LOGIN_PATH         default /v1/login
    ADMIN_TOKEN             default shivamtoken123
    EVAL_INGEST_SOURCE      default met-museum   (source used by T1)
    EVAL_HEAVY_WORKER_CMD   default "python utilities/heavy_worker.py"
    EVAL_BACKEND_DIR        default ./backend
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import psutil
import psycopg2
import requests

ROOT = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / "backend" / ".env")
except ImportError:
    pass

BASE = (os.getenv("EVAL_BASE_URL") or f"http://localhost:{os.getenv('PORT', '8000')}").rstrip("/")
LOGIN_PATH = os.getenv("EVAL_LOGIN_PATH", "/v1/login")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "shivamtoken123")
DATABASE_URL = os.getenv("DATABASE_URL")
INGEST_SOURCE = os.getenv("EVAL_INGEST_SOURCE", "met-museum")
HEAVY_CMD = os.getenv("EVAL_HEAVY_WORKER_CMD", "python utilities/heavy_worker.py")
BACKEND_DIR = os.getenv("EVAL_BACKEND_DIR", str(ROOT / "backend"))
MOCK_DIR = ROOT / "public-mock-internet"

PASS, FAIL, INCONCLUSIVE, ERROR = "PASS", "FAIL", "INCONCLUSIVE", "ERROR"
DONE_STATES = {"done", "completed", "complete", "succeeded", "success", "finished"}
FAILED_STATES = {"failed", "error"}


# ----------------------------------------------------------------- helpers
def result(status, summary, metrics=None, notes=None):
    return {"status": status, "summary": summary, "metrics": metrics or {}, "notes": notes or []}


def sql(query, params=()):
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        return cur.fetchall() if cur.description else []
    finally:
        conn.close()


def bump_cache():
    sql("UPDATE index_state SET cache_version = cache_version + 1")


def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE}{LOGIN_PATH}", json={"role": "admin", "token": ADMIN_TOKEN}, timeout=30)
    if r.status_code >= 400:
        print(f"  [warn] admin login failed ({r.status_code}) at {LOGIN_PATH}; continuing without a cookie")
    return s


def search(q, k=10, cursor=None, filters=None):
    body = {"q": q, "k": k}
    if cursor:
        body["cursor"] = cursor
    if filters:
        body["filters"] = filters
    t0 = time.perf_counter()
    r = requests.post(f"{BASE}/v1/search", json=body, timeout=30)
    elapsed = time.perf_counter() - t0
    try:
        data = r.json()
    except ValueError:
        data = None
    return r.status_code, data, elapsed


def ids_of(data):
    return [str(x["id"]) for x in (data or {}).get("results", [])]


def all_pages(q, k, max_pages=300, delay=0.0):
    ids, cursor = [], None
    for _ in range(max_pages):
        status, data, _ = search(q, k, cursor)
        if status != 200:
            raise RuntimeError(f"search returned HTTP {status}: {data}")
        ids += ids_of(data)
        cursor = data.get("next_cursor")
        if not cursor:
            break
        if delay:
            time.sleep(delay)
    return ids


def expected_refs(slug):
    """source_ref values that the mock source should produce."""
    refs, folder = set(), MOCK_DIR / slug

    def collect(obj):
        if isinstance(obj, dict) and "source_ref" in obj:
            refs.add(str(obj["source_ref"]))

    for f in folder.glob("*.jsonl"):
        if f.name == "records_update.jsonl":
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                collect(json.loads(line))
    for f in sorted((folder / "pages").glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else next(
            (v for v in data.values() if isinstance(v, list)), [])
        for obj in items:
            collect(obj)
    return refs


def worker_procs():
    found = []
    for p in psutil.process_iter(["pid", "cmdline"]):
        cmd = " ".join(p.info["cmdline"] or [])
        if "heavy_worker" in cmd and p.info["pid"] != os.getpid():
            found.append(p)
    return found


def kill_workers():
    pids = []
    for p in worker_procs():
        try:
            for child in p.children(recursive=True):
                child.kill()
            p.kill()  # SIGKILL on Linux/macOS, TerminateProcess on Windows
            pids.append(p.pid)
        except psutil.NoSuchProcess:
            pass
    return pids


# ---------------------------------------------------------------------- T1
def t1_kill_ingest():
    slug = INGEST_SOURCE
    expected = expected_refs(slug)
    if not expected:
        return result(INCONCLUSIVE, f"could not read expected records for '{slug}' from {MOCK_DIR / slug}")
    total = len(expected)
    s = admin_session()

    sql("DELETE FROM records WHERE source = %s", (slug,))
    sql("DELETE FROM jobs WHERE source = %s AND type = 'ingest'", (slug,))
    sql("UPDATE sources SET cursor = NULL WHERE slug = %s", (slug,))

    r = s.post(f"{BASE}/v1/ingest/{slug}/run", timeout=30)
    if r.status_code >= 400:
        return result(FAIL, f"could not start ingest: HTTP {r.status_code} {r.text[:200]}")
    run_id = r.json().get("run_id")

    killed, deadline = [], time.time() + 60
    while time.time() < deadline:
        n = sql("SELECT count(*) FROM records WHERE source = %s", (slug,))[0][0]
        if n >= total:
            break
        if n >= 1:
            killed = kill_workers()
            break
        time.sleep(0.02)

    committed = sql("SELECT count(*) FROM records WHERE source = %s", (slug,))[0][0]
    cursor_after_kill = sql("SELECT cursor FROM sources WHERE slug = %s", (slug,))[0][0]
    if not killed:
        return result(INCONCLUSIVE, "no heavy worker process was found to kill (is it running?)",
                      {"records_when_checked": committed, "expected_total": total})
    if committed >= total:
        return result(INCONCLUSIVE, "ingest finished before the worker could be killed mid-batch",
                      {"records": committed, "expected_total": total})

    time.sleep(1)
    restarted = False
    if not worker_procs():
        subprocess.Popen(HEAVY_CMD, shell=True, cwd=BACKEND_DIR,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        restarted = True

    status, deadline, t_resume = None, time.time() + 180, time.time()
    while time.time() < deadline:
        if run_id is not None:
            rows = sql("SELECT status, error FROM jobs WHERE id = %s", (run_id,))
        else:
            rows = sql("SELECT status, error FROM jobs WHERE source = %s AND type = 'ingest' "
                       "ORDER BY id DESC LIMIT 1", (slug,))
        status = rows[0][0] if rows else None
        if status and status.lower() in DONE_STATES | FAILED_STATES:
            break
        time.sleep(0.5)
    resume_seconds = round(time.time() - t_resume, 1)

    refs = [r[0] for r in sql("SELECT source_ref FROM records WHERE source = %s", (slug,))]
    duplicates = len(refs) - len(set(refs))
    missing = sorted(expected - set(refs))
    final_cursor = sql("SELECT cursor FROM sources WHERE slug = %s", (slug,))[0][0]

    metrics = {
        "expected_records": total,
        "committed_at_kill": committed,
        "cursor_after_kill": cursor_after_kill,
        "final_cursor": final_cursor,
        "final_job_status": status,
        "records_in_db": len(refs),
        "duplicates": duplicates,
        "missing (gaps)": len(missing),
        "worker_restarted_by_eval": restarted,
        "seconds_to_finish_after_kill": resume_seconds,
    }
    notes = [f"example missing refs: {missing[:5]}"] if missing else []
    notes.append("cursor values are reported, not asserted, because the cursor format is source specific")
    if not status or status.lower() not in DONE_STATES:
        return result(FAIL, f"ingest did not finish after the kill (job status: {status})", metrics, notes)
    if duplicates or missing:
        return result(FAIL, f"{duplicates} duplicates and {len(missing)} gaps after resume", metrics, notes)
    return result(PASS, f"killed at {committed}/{total} records; resumed with no duplicates and no gaps",
                  metrics, notes)


# ---------------------------------------------------------------------- T3
def t3_unknown_licence():
    rows = sql("""SELECT r.id::text, r.title, r.caption FROM records r
                  JOIN sources so ON so.slug = r.source AND so.status = 'enabled'
                  WHERE r.license = 'unknown' LIMIT 10""")
    if not rows:
        return result(INCONCLUSIVE, "no unknown-licence record in an enabled source; ingest 'user-uploads' first")
    unknown_ids = {r[0] for r in rows}
    leaks, searches, pages_read = [], 0, 0
    for rid, title, caption in rows:
        for text in filter(None, [title, caption]):
            for filters in (None, {"license": ["unknown"]}):
                searches += 1
                cursor = None
                for _ in range(100):
                    status, data, _ = search(text, 100, cursor, filters)
                    if status != 200:
                        break
                    pages_read += 1
                    leaks += [i for i in ids_of(data) if i in unknown_ids]
                    cursor = data.get("next_cursor")
                    if not cursor:
                        break
    metrics = {"unknown_licence_records_tested": len(unknown_ids), "searches_run": searches,
               "pages_read": pages_read, "leaks": len(leaks)}
    if leaks:
        return result(FAIL, f"{len(leaks)} unknown-licence results leaked", metrics, [f"leaked ids: {leaks[:5]}"])
    return result(PASS, "no unknown-licence record appeared in any result page", metrics)


# ---------------------------------------------------------------------- T4
def t4_version_mismatch():
    s = admin_session()
    original = sql("SELECT live_version FROM index_state LIMIT 1")[0][0]
    bogus = "eval-v999-no-vectors"
    metrics = {"original_live_version": original, "switched_to": bogus}
    try:
        sw = s.post(f"{BASE}/v1/index/switch", json={"active_version": bogus}, timeout=30)
        metrics["switch_http_status"] = sw.status_code
        if sw.status_code >= 400:
            return result(PASS, f"switch to a version without vectors was refused (HTTP {sw.status_code})", metrics)
        status, data, _ = search("sunset over the sea", 10)
        metrics["search_http_status"] = status
        metrics["results_returned"] = len(ids_of(data))
        if status >= 400:
            return result(PASS, f"search against mismatched vectors was refused loudly (HTTP {status})", metrics)
        if ids_of(data):
            return result(FAIL, "results were returned although no vector has the live version", metrics)
        return result(FAIL, "no loud refusal: switch accepted and search returned an empty HTTP 200", metrics,
                      ["a silent empty result hides the version problem; expected an error status"])
    finally:
        sql("UPDATE index_state SET live_version = %s, cache_version = cache_version + 1", (original,))


# ---------------------------------------------------------------------- T6
def t6_takedown_cached_pages():
    s = admin_session()
    ks = (30, 60, 100)  # three different (q, k) pairs = three different cache entries
    cands = sql("""SELECT r.id::text, r.title, r.caption FROM records r
                   JOIN sources so ON so.slug = r.source AND so.status = 'enabled'
                   WHERE r.license <> 'unknown' AND COALESCE(r.status, 'active') = 'active'
                   ORDER BY random() LIMIT 25""")
    target, variants = None, []
    for rid, title, caption in cands:
        for text in filter(None, [title, caption]):
            hits = []
            for k in ks:
                status, data, _ = search(text, k)
                if status == 200 and rid in ids_of(data):
                    hits.append((text, k))
            if len(hits) == len(ks):
                target, variants = rid, hits
                break
        if target:
            break
    if not target:
        return result(INCONCLUSIVE, "could not find a record that appears in three different result pages")

    try:
        for text, k in variants * 2:  # warm every page twice so each one is cached
            search(text, k)
        t0 = time.perf_counter()
        r = s.post(f"{BASE}/v1/takedown", json={"record_id": target, "reason": "eval T6"}, timeout=30)
        takedown_seconds = time.perf_counter() - t0
        if r.status_code >= 400:
            return result(FAIL, f"takedown request failed: HTTP {r.status_code} {r.text[:200]}")
        still_visible, errors = [], []
        for text, k in variants:
            status, data, _ = search(text, k)
            if status != 200:
                errors.append(k)
            elif target in ids_of(data):
                still_visible.append(k)
        total_seconds = time.perf_counter() - t0
        metrics = {"record_id": target, "pages_checked": len(variants),
                   "pages_still_showing_record": len(still_visible),
                   "takedown_request_seconds": round(takedown_seconds, 3),
                   "takedown_plus_verification_seconds": round(total_seconds, 3)}
        if still_visible or errors:
            return result(FAIL, f"record still visible in {len(still_visible)}/{len(variants)} pages "
                                f"(errors: {len(errors)})", metrics,
                          ["check that search filters on records.status = 'active' and that the cache "
                           "key includes cache_version"])
        if total_seconds > 1.0:
            return result(FAIL, f"record gone, but it took {total_seconds:.2f}s (limit 1s)", metrics)
        return result(PASS, f"record gone from all {len(variants)} cached pages in {total_seconds:.2f}s", metrics)
    finally:
        sql("UPDATE records SET status = 'active' WHERE id::text = %s", (target,))
        bump_cache()


# ---------------------------------------------------------------------- T9
def t9_paging_during_ingest():
    live = sql("SELECT live_version FROM index_state LIMIT 1")[0][0]
    sample = sql("""SELECT r.title FROM records r
                    JOIN sources so ON so.slug = r.source AND so.status = 'enabled'
                    WHERE r.license <> 'unknown' AND COALESCE(r.status, 'active') = 'active'
                    AND r.title IS NOT NULL LIMIT 1""")
    if not sample:
        return result(INCONCLUSIVE, "no searchable records in the database")
    q, k = sample[0][0], 10

    cols = sql("""SELECT column_name, data_type, column_default, is_identity, is_generated
                  FROM information_schema.columns
                  WHERE table_schema = 'public' AND table_name = 'records' ORDER BY ordinal_position""")
    names = [c[0] for c in cols if c[0] != "id" and c[4] != "ALWAYS"]
    id_col = next((c for c in cols if c[0] == "id"), None)
    id_expr = None
    if id_col and id_col[2] is None and id_col[3] != "YES":
        id_expr = ("gen_random_uuid()" if id_col[1] == "uuid"
                   else "md5(random()::text || g::text || clock_timestamp()::text)")
    insert_cols = (['"id"'] if id_expr else []) + [f'"{c}"' for c in names]
    select_cols = ([id_expr] if id_expr else []) + [
        "'eval9-' || g || '-' || r.source_ref" if c == "source_ref" else f'r."{c}"' for c in names]
    insert_sql = f"""
        INSERT INTO records ({", ".join(insert_cols)})
        SELECT {", ".join(select_cols)}
        FROM (SELECT * FROM records WHERE license <> 'unknown'
              AND COALESCE(status, 'active') = 'active' AND text_ver = %s LIMIT 50) r
        CROSS JOIN generate_series(%s, %s) g"""

    baseline = all_pages(q, k)
    inserted, insert_errors = [0], []

    def ingest_500():
        try:
            for batch in range(10):  # 10 batches x 50 rows = 500 new rows
                sql(insert_sql, (live, batch + 1, batch + 1))
                inserted[0] += 50
                time.sleep(0.15)
        except Exception as exc:  # reported below
            insert_errors.append(str(exc))

    try:
        thread = threading.Thread(target=ingest_500)
        thread.start()
        paged = all_pages(q, k, delay=0.1)
        thread.join()
    finally:
        sql("DELETE FROM records WHERE source_ref LIKE 'eval9-%'")
        bump_cache()

    if insert_errors:
        return result(ERROR, f"could not insert test rows: {insert_errors[0]}")
    duplicates = len(paged) - len(set(paged))
    skipped = [i for i in baseline if i not in set(paged)]
    metrics = {"rows_ingested_while_paging": inserted[0], "page_size": k,
               "results_before_ingest": len(baseline), "results_returned_while_ingesting": len(paged),
               "duplicate_results": duplicates, "skipped_results": len(skipped)}
    if duplicates or skipped:
        return result(FAIL, f"{duplicates} duplicates and {len(skipped)} skipped results while paging",
                      metrics, ["offset-based cursors shift when rows are inserted; use a keyset cursor "
                                "or pin the cursor to a snapshot (for example a max id or timestamp)"])
    return result(PASS, "paging was stable while 500 rows were ingested", metrics)


# --------------------------------------------------------------------- T12
def t12_hostile_queries():
    cases = {
        "10,000 characters": "a" * 10_000,
        "sql injection": "'; DROP TABLE records; --",
        "boolean injection": "x' OR '1'='1",
        "null bytes and unicode": "\u0000\u202e" + "\U0001F600" * 50,
    }
    metrics, problems = {}, []
    for name, text in cases.items():
        try:
            status, _, elapsed = search(text, 10)
        except requests.RequestException as exc:
            problems.append(f"{name}: request failed ({exc.__class__.__name__})")
            continue
        metrics[f"{name}: http / seconds"] = f"{status} / {elapsed:.3f}"
        if status >= 500:
            problems.append(f"{name}: HTTP {status}")
        if elapsed > 1.0:
            problems.append(f"{name}: took {elapsed:.2f}s")
    intact = sql("SELECT to_regclass('public.records') IS NOT NULL")[0][0]
    metrics["records table still exists"] = intact
    if not intact:
        problems.append("records table is gone")
    if problems:
        return result(FAIL, "; ".join(problems), metrics)
    return result(PASS, "all hostile queries were answered quickly with a non-5xx status", metrics)


TESTS = [
    ("T1", "kill -9 the ingest mid-batch", t1_kill_ingest),
    ("T3", "unknown licence never appears", t3_unknown_licence),
    ("T4", "version mismatch is refused loudly", t4_version_mismatch),
    ("T6", "takedown disappears from cached pages within 1 s", t6_takedown_cached_pages),
    ("T9", "paging is stable while 500 rows are ingested", t9_paging_during_ingest),
    ("T12", "huge and injection-style queries", t12_hostile_queries),
]


# ------------------------------------------------------------------ report
def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "unknown"


def write_report(rows, path):
    lines = [
        "# EVAL_RESULTS",
        "",
        "Output of `make eval` (`python eval.py`). Numbers we are not happy with are kept on purpose.",
        "",
        f"- Run at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"- Git commit: {git_commit()}",
        f"- Server: {BASE}",
        "",
        "## Summary",
        "",
        "| # | Scenario | Result | Finding |",
        "|---|---|---|---|",
    ]
    for tid, name, res, secs in rows:
        lines.append(f"| {tid} | {name} | **{res['status']}** | {res['summary'].replace('|', '/')} |")

    bad = [r for r in rows if r[2]["status"] != PASS]
    lines += ["", "## Numbers we are not happy with", ""]
    if not bad:
        lines.append("None in this run.")
    for tid, name, res, secs in bad:
        lines.append(f"- **{tid} ({res['status']})**: {res['summary']}")

    lines += ["", "## Details", ""]
    for tid, name, res, secs in rows:
        lines += [f"### {tid} - {name}", "", f"Result: **{res['status']}** ({secs:.1f}s)", "",
                  res["summary"], ""]
        for key, value in res["metrics"].items():
            lines.append(f"- {key}: `{value}`")
        for note in res["notes"]:
            lines.append(f"- note: {note}")
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="comma separated test ids, e.g. T3,T6")
    parser.add_argument("--output", default=str(ROOT / "EVAL_RESULTS.md"))
    args = parser.parse_args()

    if not DATABASE_URL:
        sys.exit("DATABASE_URL is not set (export it or put it in backend/.env)")
    try:
        sql("SELECT 1")
        requests.get(f"{BASE}/metrics", timeout=10)
    except Exception as exc:
        sys.exit(f"Preflight failed: {exc.__class__.__name__}: {exc}")

    wanted = {t.strip().upper() for t in args.only.split(",")} if args.only else None
    rows = []
    for tid, name, fn in TESTS:
        if wanted and tid not in wanted:
            continue
        print(f"{tid}: {name} ...", flush=True)
        t0 = time.time()
        try:
            res = fn()
        except Exception as exc:
            res = result(ERROR, f"{exc.__class__.__name__}: {exc}", notes=[traceback.format_exc(limit=3)])
        rows.append((tid, name, res, time.time() - t0))
        print(f"  -> {res['status']}: {res['summary']}", flush=True)

    write_report(rows, args.output)
    print(f"\nWrote {args.output}")
    sys.exit(1 if any(r[2]["status"] in (FAIL, ERROR) for r in rows) else 0)


if __name__ == "__main__":
    main()