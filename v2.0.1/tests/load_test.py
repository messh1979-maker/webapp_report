#!/usr/bin/env python3
"""Small dependency-free concurrent smoke/load test.

Example:
  python tests/load_test.py --url http://127.0.0.1:8000 \
      --username admin --password 'your-password' --users 50 --requests 5

Each virtual user creates its own authenticated session and requests the main
read-heavy pages. Exit code is non-zero on HTTP errors or excessive latency.
"""
import argparse
import concurrent.futures
import http.cookiejar
import re
import statistics
import time
import urllib.parse
import urllib.request

TOKEN_RE = re.compile(r'name="csrf_token" value="([^"]+)"')
PATHS = ("/", "/buildings", "/consumptions", "/reports")


def virtual_user(base_url, username, password, requests_per_user):
    cookies = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
    durations = []
    with opener.open(base_url + "/login", timeout=20) as response:
        html = response.read().decode("utf-8")
    match = TOKEN_RE.search(html)
    if not match:
        raise RuntimeError("CSRF token not found")
    data = urllib.parse.urlencode({"csrf_token": match.group(1), "username": username, "password": password}).encode()
    request = urllib.request.Request(base_url + "/login", data=data, method="POST")
    with opener.open(request, timeout=20) as response:
        response.read()
        if response.status != 200:
            raise RuntimeError(f"login status={response.status}")
    for i in range(requests_per_user):
        started = time.perf_counter()
        with opener.open(base_url + PATHS[i % len(PATHS)], timeout=20) as response:
            response.read()
            if response.status != 200:
                raise RuntimeError(f"status={response.status}")
        durations.append(time.perf_counter() - started)
    return durations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--users", type=int, default=50)
    parser.add_argument("--requests", type=int, default=5)
    parser.add_argument("--max-p95", type=float, default=2.0)
    args = parser.parse_args()
    started = time.perf_counter()
    durations, errors = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.users) as pool:
        futures = [pool.submit(virtual_user, args.url.rstrip("/"), args.username, args.password, args.requests) for _ in range(args.users)]
        for future in concurrent.futures.as_completed(futures):
            try:
                durations.extend(future.result())
            except Exception as exc:
                errors.append(str(exc))
    elapsed = time.perf_counter() - started
    ordered = sorted(durations)
    p95 = ordered[max(0, int(len(ordered) * 0.95) - 1)] if ordered else float("inf")
    print(f"users={args.users} requests={len(durations)} errors={len(errors)} elapsed={elapsed:.2f}s")
    print(f"avg={statistics.mean(durations):.3f}s p95={p95:.3f}s max={max(durations, default=0):.3f}s")
    for error in errors[:10]:
        print("ERROR:", error)
    raise SystemExit(1 if errors or p95 > args.max_p95 else 0)


if __name__ == "__main__":
    main()
