import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

BASE_URL = "http://127.0.0.1:5000"

routes = [
    ["POST", "/v1/search"],
    ["GET", "/v1/similar/test123"],
    ["POST", "/v1/takedown"],
    ["POST", "/v1/sources/test123/enable"],
    ["POST", "/v1/index/switch"],
    ["GET", "/v1/ingest/test123"],
    ["POST", "/v1/ingest/test123/run"],
    ["POST", "/v1/index/reembed"],
    ["GET", "/metrics"],
]

folder = Path(__file__).resolve().parent / "eval_results"
folder.mkdir(exist_ok=True)
file_path = folder / "phase1_results.md"


def send(method, path):
    req = urllib.request.Request(BASE_URL + path, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=5)
        return r.status, r.headers.get("Allow"), None
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Allow"), None
    except Exception as e:
        return None, None, str(e)


now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
lines = ["# Phase 1: route reachability", "", "- Time: " + now, "- Base URL: " + BASE_URL, ""]

code, allow, err = send("GET", "/")
if err:
    print("Backend is not running at " + BASE_URL)
    print(err)
    lines.append("**Backend is not running.**")
    lines.append("")
    lines.append("Reason: " + err)
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    exit()

print("Server is up at " + BASE_URL)

lines.append("| Method | Path | Result | Route check | Real call |")
lines.append("|---|---|---|---|---|")
passed = 0

for method, path in routes:
    code, allow, err = send("OPTIONS", path)

    if err:
        result = "FAIL"
        note = "not reached"
    elif code == 404:
        result = "FAIL"
        note = "404 route not found"
    elif code == 405 and method in (allow or ""):
        result = "PASS"
        note = "405, Allow = " + allow
    elif code == 405:
        result = "FAIL"
        note = "method not allowed, Allow = " + str(allow)
    else:
        result = "PASS"
        note = "status " + str(code)

    real = "skipped"
    if method == "GET":
        code2, allow2, err2 = send("GET", path)
        if err2:
            real = "not reached"
        else:
            real = "GET -> " + str(code2)

    if result == "PASS":
        passed = passed + 1

    print(method, path, result, "|", note, "|", real)
    lines.append("| " + method + " | `" + path + "` | " + result + " | " + note + " | " + real + " |")

total = len(routes)
print(str(passed) + "/" + str(total) + " routes reachable")

lines.insert(4, "- Result: " + str(passed) + "/" + str(total) + " routes reachable")
lines.append("")
lines.append("POST routes are only checked with OPTIONS, because a real POST can change data.")
file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("Saved to " + str(file_path))








