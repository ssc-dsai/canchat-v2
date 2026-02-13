import asyncio
import inspect
import logging
import threading
from functools import wraps
from typing import Optional

from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    HnswConfigDiff,
    MatchValue,
    PointStruct,
    ScalarQuantization,
    ScalarQuantizationConfig,
    ScalarType,
    VectorParams,
)

from open_webui.config import (
    QDRANT_API_KEY,
    QDRANT_ENABLE_QUANTIZATION,
    QDRANT_ON_DISK_HNSW,
    QDRANT_ON_DISK_PAYLOAD,
    QDRANT_ON_DISK_VECTOR,
    QDRANT_PREFER_GRPC,
    QDRANT_TIMEOUT_SECONDS,
    QDRANT_URL,
)
from open_webui.env import SRC_LOG_LEVELS
from open_webui.retrieval.vector.locks import get_collection_lock_manager
from open_webui.retrieval.vector.main import GetResult, SearchResult, VectorItem

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def with_qdrant_client(func):
    """Inject the loop-scoped Qdrant client for async instance methods."""

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        client = await self._get_client()
        return await func(self, client, *args, **kwargs)

    return wrapper


# Global distributed lock manager for collection-level synchronization.
_collection_lock_manager = get_collection_lock_manager()


class QdrantClient:
    def __init__(self):
        self._client: Optional[AsyncQdrantClient] = None
        self._client_loop_id: Optional[int] = None
        # NOTE: threading.Lock is intentional here because these sections only do
        # fast synchronous reference swaps. Never add await calls while holding it.
        self._client_lock = threading.Lock()
        self._cleanup_tasks: set[asyncio.Task] = set()

    def _build_client(self) -> AsyncQdrantClient:
        return AsyncQdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=int(QDRANT_TIMEOUT_SECONDS),
            prefer_grpc=QDRANT_PREFER_GRPC,
        )

    @staticmethod
    async def _maybe_await(value):
        if inspect.isawaitable(value):
            return await value
        return value

    async def _close_client(self, client: Optional[AsyncQdrantClient]) -> None:
        if client is None:
            return

        try:
            close_method = getattr(client, "aclose", None)
            if close_method is not None:
                await self._maybe_await(close_method())
                return

            close_method = getattr(client, "close", None)
            if close_method is not None:
                await self._maybe_await(close_method())
        except Exception as e:
            log.debug(f"Error closing stale Qdrant client: {type(e).__name__}: {e}")

    def _swap_client_for_current_loop(
        self,
    ) -> tuple[AsyncQdrantClient, Optional[AsyncQdrantClient]]:
        """Return a client for the current asyncio loop.

        Fast path returns the cached client when the loop matches. On loop
        mismatch (or no client) this synchronously swaps in a new client under
        `self._client_lock` and returns (new_client, old_client). Caller must
        close the stale client (await or schedule cleanup).
        """
        try:
            current_loop_id = id(asyncio.get_running_loop())
        except RuntimeError:
            # No running loop in this thread — treat loop id as `None`.
            current_loop_id = None

        # Keep this section short and synchronous; do not await while holding the lock.
        with self._client_lock:
            # Fast path: cached client already matches the current loop.
            if self._client is not None and self._client_loop_id == current_loop_id:
                return self._client, None

            # Swap: create a new client for the current loop and return the old one.
            old_client = self._client
            old_loop_id = self._client_loop_id

            # Build the new client (caller will close the old one).
            self._client = self._build_client()
            self._client_loop_id = current_loop_id

            if old_client is not None:
                log.info(
                    "Swapped Qdrant client due to event-loop change: "
                    f"old_loop={old_loop_id}, new_loop={current_loop_id}"
                )

            return self._client, old_client

    def _track_cleanup_task(self, task: asyncio.Task) -> None:
        """Track fire-and-forget cleanup tasks so shutdown can await them."""
        with self._client_lock:
            self._cleanup_tasks.add(task)

        def _on_done(done_task: asyncio.Task) -> None:
            with self._client_lock:
                self._cleanup_tasks.discard(done_task)
            try:
                exc = done_task.exception()
            except asyncio.CancelledError:
                return
            if exc:
                log.debug(
                    "Background stale-client cleanup task failed: "
                    f"{type(exc).__name__}: {exc}"
                )

        task.add_done_callback(_on_done)

    async def _get_client(self) -> AsyncQdrantClient:
        client, stale_client = self._swap_client_for_current_loop()
        if stale_client is not None and stale_client is not client:
            await self._close_client(stale_client)
        return client

    @property
    def client(self):
        """
        Compatibility accessor.

        Returns a loop-aware cached client synchronously and schedules cleanup
        of stale client instances when called within a running event loop.
        """
        client, stale_client = self._swap_client_for_current_loop()
        if stale_client is not None and stale_client is not client:
            try:
                task = asyncio.get_running_loop().create_task(
                    self._close_client(stale_client)
                )
                self._track_cleanup_task(task)
            except RuntimeError:
                pass
        return client

    async def close(self):
        """Close the currently cached client, if any."""
        with self._client_lock:
            pending_cleanup_tasks = tuple(
                task for task in self._cleanup_tasks if not task.done()
            )

        if pending_cleanup_tasks:
            await asyncio.gather(*pending_cleanup_tasks, return_exceptions=True)

        stale_client = None
        with self._client_lock:
            stale_client = self._client
            self._client = None
            self._client_loop_id = None
        await self._close_client(stale_client)

    @staticmethod
    def _build_filter(filter_data: Optional[dict]) -> Optional[Filter]:
        if not filter_data:
            return None

        conditions = [
            FieldCondition(key=key, match=MatchValue(value=value))
            for key, value in filter_data.items()
        ]
        return Filter(must=conditions)

    @with_qdrant_client
    async def has_collection(
        self, client: AsyncQdrantClient, collection_name: str
    ) -> bool:
        return await client.collection_exists(collection_name=collection_name)

    @with_qdrant_client
    async def list_collections(self, client: AsyncQdrantClient) -> list[str]:
        collections_response = await client.get_collections()
        return [collection.name for collection in collections_response.collections]

    def _result_to_get_result(self, result) -> GetResult:
        ids = []
        documents = []
        metadatas = []
        # Check if result is valid and has records
        if result and len(result) > 0 and len(result[0]) > 0:
            # Iterate over the tuple of records
            for record in result[0]:
                ids.append([record.id])
                documents.append([record.payload["text"]])
                metadatas.append([record.payload["metadata"]])

        return GetResult(
            **{
                "ids": ids,
                "documents": documents,
                "metadatas": metadatas,
            }
        )

    def _result_to_search_result(self, result) -> SearchResult:
        ids = []
        distances = []
        documents = []
        metadatas = []

        for point in result.points:
            ids.append([point.id])
            distances.append([point.score])
            documents.append([point.payload["text"]])
            metadatas.append([point.payload["metadata"]])

        return SearchResult(
            **{
                "ids": ids,
                "distances": distances,
                "documents": documents,
                "metadatas": metadatas,
            }
        )

    @with_qdrant_client
    async def get_collection_sample_metadata(
        self, client: AsyncQdrantClient, collection_name: str
    ) -> Optional[dict]:
        """Get metadata from a sample point in the collection to check properties like age."""
        try:
            points, _ = await client.scroll(
                collection_name=collection_name,
                limit=1,
                with_payload=True,
            )
            if points and len(points) > 0:
                point = points[0]
                if hasattr(point, "payload") and point.payload:
                    return point.payload.get("metadata", {})
            return None
        except Exception:
            return None

    @with_qdrant_client
    async def _delete_collection_unlocked(
        self, client: AsyncQdrantClient, collection_name: str
    ):
        try:
            result = await client.delete_collection(collection_name=collection_name)
            log.info(f"Deleted collection: {collection_name}")
            return result
        except Exception as e:
            if not await client.collection_exists(collection_name=collection_name):
                return True
            log.error(
                f"Error deleting collection {collection_name}: {type(e).__name__}: {e}"
            )
            raise

    async def delete_collection(self, collection_name: str):
        """
        Delete the collection based on the collection name.
        Uses distributed Redis locking to prevent race conditions across instances.
        """
        async with _collection_lock_manager.acquire_lock(collection_name):
            return await self._delete_collection_unlocked(collection_name)

    @with_qdrant_client
    async def search(
        self,
        client: AsyncQdrantClient,
        collection_name: str,
        vectors: list[list[float | int]],
        limit: int,
    ) -> Optional[SearchResult]:
        result = await client.query_points(
            collection_name=collection_name,
            query=vectors,
            limit=limit,
            with_payload=True,
        )
        return self._result_to_search_result(result)

    @with_qdrant_client
    async def query(
        self,
        client: AsyncQdrantClient,
        collection_name: str,
        filter: dict,
        limit: Optional[int] = None,
    ) -> Optional[GetResult]:
        try:
            if not await client.collection_exists(collection_name=collection_name):
                return None

            points, _ = await client.scroll(
                collection_name=collection_name,
                scroll_filter=self._build_filter(filter),
                limit=limit or 1,
            )

            return self._result_to_get_result(points)
        except Exception as e:
            log.error(f"Error querying Qdrant collection {collection_name}: {e}")
            return None

    @with_qdrant_client
    async def get(
        self, client: AsyncQdrantClient, collection_name: str
    ) -> Optional[GetResult]:
        points = await client.count(collection_name=collection_name)
        if points.count:
            result = await client.scroll(
                collection_name=collection_name,
                with_payload=True,
                limit=points.count,
            )

            return self._result_to_get_result(result)

        return None

    async def insert(
        self,
        collection_name: str,
        items: list[VectorItem],
    ):
        return await self.upsert(
            collection_name=collection_name,
            items=items,
        )

    async def _ensure_collection_exists(
        self,
        client: AsyncQdrantClient,
        collection_name: str,
        items: list[VectorItem],
    ) -> None:
        if await client.collection_exists(collection_name=collection_name):
            return

        quantization_config = (
            ScalarQuantization(
                scalar=ScalarQuantizationConfig(type=ScalarType.INT8, always_ram=True)
            )
            if QDRANT_ENABLE_QUANTIZATION
            else None
        )

        try:
            await client.create_collection(
                collection_name=collection_name,
                on_disk_payload=QDRANT_ON_DISK_PAYLOAD,
                hnsw_config=HnswConfigDiff(on_disk=QDRANT_ON_DISK_HNSW),
                vectors_config=VectorParams(
                    size=len(items[0]["vector"]),
                    distance=Distance.COSINE,
                    on_disk=QDRANT_ON_DISK_VECTOR,
                    multivector_config=models.MultiVectorConfig(
                        comparator=models.MultiVectorComparator.MAX_SIM
                    ),
                    quantization_config=quantization_config,
                ),
            )
            log.info(f"Created new collection: {collection_name}")
        except Exception as e:
            if await client.collection_exists(collection_name=collection_name):
                return
            log.error(
                f"Error creating collection {collection_name}: {type(e).__name__}: {e}"
            )
            raise

    @with_qdrant_client
    async def _upsert_unlocked(
        self,
        client: AsyncQdrantClient,
        collection_name: str,
        items: list[VectorItem],
    ):
        await self._ensure_collection_exists(client, collection_name, items)

        points = [
            PointStruct(
                id=item["id"],
                vector=item["vector"],
                payload={"text": item["text"], "metadata": item["metadata"]},
            )
            for item in items
        ]

        # wait=True ensures data is committed before returning.
        return await client.upsert(
            collection_name=collection_name,
            points=points,
            wait=True,
        )

    async def upsert(
        self,
        collection_name: str,
        items: list[VectorItem],
    ):
        """
        Update the items in the collection, if the items are not present, insert them.
        If the collection does not exist, it will be created.

        Uses distributed Redis locking to prevent race conditions across multiple instances.
        """
        async with _collection_lock_manager.acquire_lock(collection_name):
            return await self._upsert_unlocked(collection_name, items)

    @with_qdrant_client
    async def delete(
        self,
        client: AsyncQdrantClient,
        collection_name: str,
        ids: Optional[list[str]] = None,
        filter: Optional[dict] = None,
    ):
        if ids:
            selector = ids
        elif filter:
            selector = self._build_filter(filter)
        else:
            raise ValueError("Either ids or filter must be provided for delete()")

        return await client.delete(
            collection_name=collection_name,
            points_selector=selector,
        )

    @with_qdrant_client
    async def reset(self, client: AsyncQdrantClient):
        collection_response = await client.get_collections()

        for collection in collection_response.collections:
            await client.delete_collection(collection_name=collection.name)
