#!/usr/bin/env python3
"""Hourly uptime probe for deadbrands.co. Stdlib only.
Checks homepage, blog index, and redirect domains. Writes ops/status.json.
Exit 0 always; failures are recorded in the JSON.
"""
import datetime
import json
import os
import sys
import urllib.request

TARGETS = [
    ("homepage", "https://deadbrands.co/"),
    ("blog", "https://deadbrands.co/blog/"),
    ("deadbrands.co", "https://deadbrands.co"),
    ("davidstrausser.com", "https://davidstrausser.com"),
]
TIMEOUT = 20


def probe(url):
    handlers = [urllib.request.ProxyHandler()]
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers={"User-Agent": "DeadBrands-Uptime/1.0"})
    try:
        with opener.open(req, timeout=TIMEOUT) as r:
            body = r.read(4096)
            return r.status, r.geturl(), None
    except Exception as e:
        return 0, url, f"{type(e).__name__}: {e}"


def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    results = {}
    for name, url in TARGETS:
        status, final, err = probe(url)
        ok = status == 200 and "deadbrands.co" in final
        results[name] = {"ok": ok, "http": status, "final": final,
                         "error": err, "checked_at": now}
    payload = {"checked_at": now, "targets": results,
               "all_ok": all(v["ok"] for v in results.values())}

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    out_dir = os.path.join(repo_root, "ops")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "status.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    for name, v in results.items():
        print(f"{name}: {'OK' if v['ok'] else 'DOWN'} (http={v['http']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
