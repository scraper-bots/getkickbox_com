#!/usr/bin/env python3
"""
main.py

Minimal script, now with automatic attempts to fetch more than the default limit
by trying larger limits and several common pagination patterns.

Run:
    python3 main.py

Config (edit near the top):
- TOKEN: your bearer token (hardcoded as requested)
- MAX_SINGLE_LIMIT: first try to request this many UUIDs in one shot
- PAGINATION_LIMIT: per-page size to use when paginating (usually same as MAX_SINGLE_LIMIT)
- SAFE_TOTAL_CAP: maximum total UUIDs to fetch (safety guard)
"""

from __future__ import annotations
import copy
import json
import sys
from itertools import islice
from typing import Any, Dict, List

import pandas as pd
import requests

# ----------------- CONFIG: edit these values if needed -----------------
TOKEN = "eyJraWQiOiIxIiwiYWxnIjoiRWREU0EifQ.eyJpc3MiOiJraWNrYm94LWltcHJvdmUiLCJzdWIiOiJhNjE0ZWZjOC0zMmI4LTRjYjItYjgwYi1iYzRiZDAxOGVkOWQiLCJhdWQiOiJQQVNIQUhvbGRpbmciLCJjb250ZXh0cyI6WyJQQVNIQUhvbGRpbmciXSwiZXhwIjoxNzYwNjc3Mjg1fQ.GXMVeQ8gFXvzsV97V_NQ5adDW27AN-CmHFHbeIsoArKU4UoeXAc8RQnInoK_a_hjgJJ7PoJLCiae5ZGlMC6IDQ"   # <-- replace with your full bearer token string

SEARCH_URL = "https://api.rready.com/PASHAHolding/global-search/users"
BATCH_URL = "https://api.rready.com/PASHAHolding/users/fetchByBatch"

# Try a larger single-request limit first (increase if you want)
MAX_SINGLE_LIMIT = 2000     # first attempt requesting up to this many UUIDs in one shot

# When paginating, use this page size per request
PAGINATION_LIMIT = 1000     # per-request page size when using offset/page strategies

# Safety cap to avoid infinite loops / accidental huge fetches
SAFE_TOTAL_CAP = 20000      # stop after fetching this many UUIDs

# How many UUIDs to send per /fetchByBatch call
BATCH_SIZE = 100

# Output filenames
CSV_OUTPUT = "users.csv"
XLSX_OUTPUT = "users.xlsx"
# ----------------------------------------------------------------------

def chunked_iterable(iterable, size):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk

def flatten_dict(d: Dict[str, Any], parent: str = "") -> Dict[str, Any]:
    out = {}
    for k, v in d.items():
        key = f"{parent}.{k}" if parent else k
        if isinstance(v, dict):
            out.update(flatten_dict(v, key))
        else:
            out[key] = v
    return out

def normalize_users(users: List[Dict]) -> pd.DataFrame:
    rows = []
    keys = set()
    for u in users:
        flat = {}
        for k, v in u.items():
            if isinstance(v, dict):
                flat.update(flatten_dict(v, parent=k))
            elif isinstance(v, list):
                if all(not isinstance(x, (dict, list)) for x in v):
                    flat[k] = ", ".join(str(x) for x in v)
                else:
                    try:
                        flat[k] = json.dumps(v, ensure_ascii=False)
                    except Exception:
                        flat[k] = str(v)
            else:
                flat[k] = v
        rows.append(flat)
        keys.update(flat.keys())

    preferred = ["id", "email", "firstName", "lastName", "username", "language", "unit"]
    rest = sorted(k for k in keys if k not in preferred)
    ordered = [k for k in preferred if k in keys] + rest

    df = pd.DataFrame([{k: r.get(k, "") for k in ordered} for r in rows])
    return df

def try_post(session: requests.Session, url: str, payload: Dict, timeout: int = 30):
    try:
        resp = session.post(url, json=payload, timeout=timeout)
    except Exception as e:
        print(f"Network error when calling {url}: {e}")
        return None
    return resp

def fetch_uuids_smart(session: requests.Session, base_payload: Dict) -> List[str]:
    """
    Try to fetch UUID list, using larger limit and common pagination strategies automatically.
    Returns deduplicated list of UUID strings.
    """
    uuids_acc: List[str] = []

    payload = copy.deepcopy(base_payload)

    # 1) Try a single large request first
    payload_single = copy.deepcopy(payload)
    payload_single["limit"] = MAX_SINGLE_LIMIT
    print(f"Attempting single request with limit={MAX_SINGLE_LIMIT} ...")
    resp = try_post(session, SEARCH_URL, payload_single)
    if resp is None:
        sys.exit(2)
    if resp.status_code == 401:
        print("Unauthorized (401). Token invalid or expired.")
        sys.exit(3)
    if resp.status_code != 200:
        print(f"Search endpoint returned {resp.status_code}: {resp.text[:300]}")
        sys.exit(4)

    try:
        data = resp.json()
    except Exception as e:
        print("Failed to parse JSON from search response:", e)
        sys.exit(5)

    if not isinstance(data, list):
        print("Search response format unexpected (expected list of UUIDs).")
        sys.exit(6)

    uuids_acc.extend([u for u in data if isinstance(u, str) and u.strip()])
    print(f"Single request returned {len(data)} UUIDs.")

    # If single returned fewer than requested limit, assume all results retrieved.
    if len(data) < MAX_SINGLE_LIMIT:
        print("Less than limit returned — assuming complete. Continuing.")
        return dedupe_preserve_order(uuids_acc)

    # Otherwise we may have more. Try several pagination strategies.
    print("Response length equals requested limit — trying pagination strategies to fetch more...")

    # Strategy A: offset-style pagination using keys like 'offset', 'start', 'from'
    offset_keys = ["offset", "start", "from"]
    for key in offset_keys:
        print(f"Trying offset-style pagination with key='{key}', page_size={PAGINATION_LIMIT} ...")
        collected = list(uuids_acc)  # already have first batch; note the first batch corresponds to offset 0 only if server respects 'limit'
        offset = len(data)  # start from what we just received
        # We'll page until no more or until SAFE_TOTAL_CAP
        while True:
            if len(collected) >= SAFE_TOTAL_CAP:
                print(f"Reached safe cap {SAFE_TOTAL_CAP}; stopping offset pagination.")
                break
            payload_page = copy.deepcopy(payload)
            payload_page["limit"] = PAGINATION_LIMIT
            payload_page[key] = offset
            resp_page = try_post(session, SEARCH_URL, payload_page)
            if resp_page is None:
                break
            if resp_page.status_code != 200:
                print(f"Offset pagination ({key}) returned {resp_page.status_code}; aborting this strategy.")
                break
            try:
                page_data = resp_page.json()
            except Exception as e:
                print("Failed to parse JSON during offset pagination:", e)
                break
            if not isinstance(page_data, list) or len(page_data) == 0:
                print(f"No more results for offset key '{key}'.")
                break
            collected.extend([u for u in page_data if isinstance(u, str) and u.strip()])
            print(f"  got {len(page_data)} uuids (total collected {len(collected)})")
            if len(page_data) < PAGINATION_LIMIT:
                print("  Last page smaller than page_size -> finishing offset pagination.")
                break
            offset += len(page_data)

        if len(collected) > len(uuids_acc):
            print(f"Offset-style with key='{key}' retrieved additional UUIDs (total {len(collected)}).")
            uuids_acc = collected
            return dedupe_preserve_order(uuids_acc)
        else:
            print(f"No extra UUIDs found using key='{key}'. Trying next strategy...")

    # Strategy B: page-based pagination with 'page' + 'size' or 'page' + 'limit'
    print("Trying page-based pagination (page + size / page + limit)...")
    for page_key in ["page"]:
        for size_key in ["size", "limit"]:
            collected = list(uuids_acc)
            page = 1  # sometimes page starts at 0, sometimes 1; we'll try both variants
            for start_page in (0, 1):
                collected = list(uuids_acc)
                page = start_page
                while True:
                    if len(collected) >= SAFE_TOTAL_CAP:
                        print(f"Reached safe cap {SAFE_TOTAL_CAP}; stopping page-based pagination.")
                        break
                    payload_page = copy.deepcopy(payload)
                    payload_page[size_key] = PAGINATION_LIMIT
                    payload_page[page_key] = page
                    resp_page = try_post(session, SEARCH_URL, payload_page)
                    if resp_page is None or resp_page.status_code != 200:
                        break
                    try:
                        page_data = resp_page.json()
                    except Exception:
                        break
                    if not isinstance(page_data, list) or len(page_data) == 0:
                        break
                    collected.extend([u for u in page_data if isinstance(u, str) and u.strip()])
                    print(f"  page {page} got {len(page_data)} uuids (total {len(collected)})")
                    if len(page_data) < PAGINATION_LIMIT:
                        break
                    page += 1

                if len(collected) > len(uuids_acc):
                    print(f"Page-based pagination (page start {start_page}, size_key '{size_key}') retrieved extra UUIDs ({len(collected)})")
                    uuids_acc = collected
                    return dedupe_preserve_order(uuids_acc)

    # If nothing worked, as a last resort try requesting an even larger single limit (but bounded)
    LAST_RESORT_LIMIT = min(5000, SAFE_TOTAL_CAP)
    if LAST_RESORT_LIMIT > MAX_SINGLE_LIMIT:
        print(f"Last resort: trying larger single request limit={LAST_RESORT_LIMIT} ...")
        payload_last = copy.deepcopy(payload)
        payload_last["limit"] = LAST_RESORT_LIMIT
        resp_last = try_post(session, SEARCH_URL, payload_last)
        if resp_last and resp_last.status_code == 200:
            try:
                last_data = resp_last.json()
                if isinstance(last_data, list) and len(last_data) > len(uuids_acc):
                    uuids_acc = [u for u in last_data if isinstance(u, str) and u.strip()]
                    print(f"Last-resort request returned {len(uuids_acc)} UUIDs.")
                    return dedupe_preserve_order(uuids_acc)
            except Exception:
                pass

    # Give up and return whatever we have (deduped)
    print("Pagination strategies exhausted. Returning collected UUIDs (may be partial).")
    return dedupe_preserve_order(uuids_acc)

def dedupe_preserve_order(seq: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def main():
    if not TOKEN or TOKEN.startswith("eyJYOUR"):
        print("ERROR: Please open main.py and set TOKEN to your Bearer token string.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    session = requests.Session()
    session.headers.update(headers)

    # Base search payload: same as your original example
    base_payload = {
        "query": "*",
        "order": {"field": "firstName.keyword", "direction": "DESC"},
        "where": [
            {"field": "deleted", "match": [False], "matchMode": "EQUAL"},
            {"field": "enabled", "match": [True], "matchMode": "EQUAL"},
        ],
        # limit will be controlled by our fetching function
    }

    print("1) Fetching UUIDs (smart fetch with pagination attempts)...")
    uuids = fetch_uuids_smart(session, base_payload)
    if not uuids:
        print("No UUIDs found. Exiting.")
        sys.exit(0)

    print(f"Total UUIDs collected: {len(uuids)} (capped at SAFE_TOTAL_CAP = {SAFE_TOTAL_CAP})")
    if len(uuids) >= SAFE_TOTAL_CAP:
        print("WARNING: reached safe cap — there may be more records on the server.")

    # Now fetch full user objects in batches
    print(f"2) Fetching user objects in batches of {BATCH_SIZE} ...")
    all_users: List[Dict] = []
    for idx, chunk in enumerate(chunked_iterable(uuids, BATCH_SIZE), start=1):
        payload = {"targets": chunk}
        try:
            resp = session.post(BATCH_URL, json=payload, timeout=60)
        except Exception as e:
            print(f"Network error during batch {idx}:", e)
            sys.exit(7)

        if resp.status_code == 401:
            print("Unauthorized (401) during batch fetch. Token invalid or expired.")
            sys.exit(8)
        if resp.status_code != 200:
            print(f"Batch endpoint returned {resp.status_code} for chunk {idx}: {resp.text[:300]}")
            sys.exit(9)

        try:
            data = resp.json()
        except Exception as e:
            print(f"Failed to parse JSON for chunk {idx}:", e)
            sys.exit(10)

        if not isinstance(data, list):
            print(f"Unexpected batch response format for chunk {idx}. Expected list, got {type(data)}")
            sys.exit(11)

        print(f"  chunk {idx}: fetched {len(data)} users")
        all_users.extend(data)

    print(f"Total user objects fetched: {len(all_users)}")
    if not all_users:
        print("No users returned. Exiting.")
        sys.exit(0)

    print("Normalizing and flattening user objects...")
    df = normalize_users(all_users)

    print(f"Writing CSV -> {CSV_OUTPUT}")
    df.to_csv(CSV_OUTPUT, index=False, encoding="utf-8")

    print(f"Writing Excel -> {XLSX_OUTPUT}")
    df.to_excel(XLSX_OUTPUT, index=False)

    print("Done. Created files:")
    print(" -", CSV_OUTPUT)
    print(" -", XLSX_OUTPUT)

if __name__ == "__main__":
    main()
