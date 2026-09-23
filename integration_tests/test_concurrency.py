"""Concurrent writes against the multi-connection Postgres pool."""
from concurrent.futures import ThreadPoolExecutor

import httpx


def test_concurrent_contact_creates_all_succeed_with_distinct_ids(base_url, auth_headers, unique):
    def create(i: int) -> httpx.Response:
        return httpx.post(
            f"{base_url}/api/contacts",
            json={"name": f"Concurrent {unique} {i}", "company": "Parallel Inc"},
            headers=auth_headers,
            timeout=10,
        )

    with ThreadPoolExecutor(max_workers=10) as pool:
        responses = list(pool.map(create, range(20)))

    statuses = [r.status_code for r in responses]
    assert statuses == [201] * 20, statuses
    assert len({r.json()["id"] for r in responses}) == 20
