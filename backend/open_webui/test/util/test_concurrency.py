#!/usr/bin/env python
"""Smoke tests that exercise concurrent uploads and retrievals through the lock manager."""

import asyncio
import sys
import time
import uuid
import os
from pathlib import Path

# Ensure `backend` is on sys.path so `open_webui` package imports resolve
# when running this test from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from qdrant_client.http.exceptions import UnexpectedResponse

# Allow running tests without explicit environment variables by falling
# back to sensible localhost defaults for development environments.
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

from open_webui.retrieval.vector.dbs.qdrant import QdrantClient
from open_webui.retrieval.vector.locks import get_collection_lock_manager


def _make_vector(base: float = 0.1, length: int = 8) -> list[float]:
    """Return a deterministic vector for a document."""
    return [base + i * 0.01 for i in range(length)]


def _make_document(doc_id: str, text: str, metadata: dict | None = None) -> dict:
    """Build the dict payload that Qdrant expects."""
    return {
        "id": doc_id,
        "text": text,
        "vector": _make_vector(base=hash(doc_id) % 10),
        "metadata": metadata or {"origin": "concurrent-test"},
    }


async def _collect_document_ids(
    client: QdrantClient, collection_name: str
) -> list[str]:
    """Fetch all stored point IDs for the collection."""
    try:
        points, _ = await client.client.scroll(
            collection_name=collection_name,
            with_payload=False,
            limit=200,
        )
    except UnexpectedResponse as exc:
        if "Not found" in str(exc):
            return []
        raise
    return [str(point.id) for point in points]


async def _search_for_document(
    client: QdrantClient,
    collection_name: str,
    target_id: str,
    vector: list[float],
) -> bool:
    """Return True if a search for the provided vector yields the target ID."""
    try:
        result = await client.search(
            collection_name=collection_name,
            vectors=[vector],
            limit=1,
        )
    except UnexpectedResponse as exc:
        if "Not found" in str(exc):
            return False
        raise

    if result and result.ids:
        for row in result.ids:
            if target_id in row:
                return True
    return False


async def _upload_document(
    manager,
    client: QdrantClient,
    collection_name: str,
    doc_id: str,
    work_delay: float,
    active_counter: list[int],
    counter_lock: asyncio.Lock,
) -> str:
    """Acquire the collection lock, upsert the document, and hold the lock briefly."""
    display_id = doc_id[:8]
    async with manager.acquire_lock(collection_name, timeout_secs=60):
        async with counter_lock:
            active_counter[0] += 1
            if active_counter[0] > 1:
                raise RuntimeError("Lock was not exclusive")

        print(f"    [upload {display_id}] entered lock, sleeping {work_delay}s")
        await client.upsert(
            collection_name=collection_name,
            items=[_make_document(doc_id, f"text-{doc_id}")],
            already_locked=True,
        )

        await asyncio.sleep(work_delay)

        async with counter_lock:
            active_counter[0] -= 1

        print(f"    [upload {display_id}] released lock")

    return doc_id


async def test_concurrent_uploads_same_collection() -> bool:
    """Verify the Redis lock serializes two simultaneous uploads on one collection."""
    client = QdrantClient()
    manager = get_collection_lock_manager()
    collection_name = f"concurrent-upload-{uuid.uuid4().hex[:8]}"
    await client.delete_collection(collection_name=collection_name)

    active_counter = [0]
    counter_lock = asyncio.Lock()
    work_delays = [0.8, 0.6, 0.4]

    print("\nScenario 1: concurrent uploads to the same collection")
    print(" - Starting multiple upload tasks that should not overlap inside the lock")

    doc_ids = [str(uuid.uuid4()) for _ in range(3)]
    tasks = [
        asyncio.create_task(
            _upload_document(
                manager,
                client,
                collection_name,
                doc_ids[i],
                work_delays[i % len(work_delays)],
                active_counter,
                counter_lock,
            )
        )
        for i in range(len(doc_ids))
    ]

    await asyncio.gather(*tasks)

    ids = await _collect_document_ids(client, collection_name)
    count = len(ids)

    if count != len(tasks):
        print(f"✗ Expected {len(tasks)} documents, found {count}")
        success = False
    else:
        print(f"✓ All {count} uploads committed with lock protection")
        success = True

    await client.delete_collection(collection_name=collection_name)
    return success


async def _retrieval_worker(
    client: QdrantClient,
    collection_name: str,
    target_id: str,
    vector: list[float],
    timeout: float = 16.0,
) -> bool:
    """Poll the collection until the target document appears via search."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if await _search_for_document(client, collection_name, target_id, vector):
            print(f"    [retriever] saw {target_id}")
            return True
        await asyncio.sleep(0.25)
    print(f"    [retriever] timed out waiting for {target_id}")
    return False


async def test_concurrent_upload_and_retrieve() -> bool:
    """Ensure retrievals can run while uploads hold the lock."""
    client = QdrantClient()
    manager = get_collection_lock_manager()
    collection_name = f"concurrent-upload-retrieve-{uuid.uuid4().hex[:8]}"
    await client.delete_collection(collection_name=collection_name)

    target_id = str(uuid.uuid4())
    target_vector = _make_vector(base=hash(target_id) % 10)

    async def long_upload():
        async with manager.acquire_lock(collection_name, timeout_secs=60):
            print("    [upload-and-retrieve] holding lock for 1.2s")
            await client.upsert(
                collection_name=collection_name,
                items=[_make_document(target_id, "retrieval-text")],
                already_locked=True,
            )
            await asyncio.sleep(1.2)
            print("    [upload-and-retrieve] releasing lock")

    print("\nScenario 2: concurrent upload vs retrieval")
    print(" - Launching one long upload plus two retrievers")

    retrieval_tasks = [
        asyncio.create_task(
            _retrieval_worker(
                client,
                collection_name,
                target_id,
                target_vector,
            )
        )
        for _ in range(2)
    ]
    upload_task = asyncio.create_task(long_upload())

    results = await asyncio.gather(upload_task, *retrieval_tasks)
    retriever_success = any(result for result in results[1:])

    if not retriever_success:
        print("✗ Retrieval never saw the document")
        success = False
    else:
        print("✓ Retrievals observed the document while upload held the lock")
        success = True

    await client.delete_collection(collection_name=collection_name)
    return success


async def run_all_scenarios() -> bool:
    """Run every concurrent scenario and return True if all succeed."""
    scenarios = [
        test_concurrent_uploads_same_collection,
        test_concurrent_upload_and_retrieve,
    ]

    overall = True
    for scenario in scenarios:
        result = await scenario()
        overall = overall and result
        await asyncio.sleep(0.1)
    return overall


async def main() -> int:
    try:
        success = await run_all_scenarios()
        if success:
            print("\n✓ Concurrent operation smoke tests passed")
            return 0
        print("\n✗ Some concurrent scenarios failed")
        return 1
    except Exception as exc:
        print(f"✗ Test harness failed: {exc}")
        raise


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
