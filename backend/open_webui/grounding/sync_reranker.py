import logging

from asyncio import Semaphore, to_thread
from collections import deque
from txtai.pipeline import Reranker

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["GROUNDING"])


class SyncReranker(Reranker):
    _num_reranker: int = 3
    _semaphore: Semaphore
    _rerankers: deque[Reranker]

    def __init__(self, embeddings, similarity):
        self._semaphore = Semaphore(self._num_reranker)
        self._rerankers = deque(maxlen=3)

        for x in range(self._num_reranker):
            log.info(f"Creating reranker {x} of {self._num_reranker}")
            self._rerankers.append(
                Reranker(embeddings=embeddings, similarity=similarity)
            )

    async def __call__(self, query, limit=3, factor=10, **kwargs):
        """
        Runs an embeddings search and re-ranks the results using a Similarity pipeline.

        This function calls it in an async manner and allows for multiple rerankers to be used to prevent concurrency issues.

        Args:
          query: query text|list
          limit: maximum results
          factor: factor to multiply limit by for the initial embeddings search
          kwargs: additional arguments to pass to embeddings search

        Returns:
          list of query results rescored using a Similarity pipeline
        """
        async with self._semaphore:
            try:
                reranker: Reranker = self._rerankers.pop()

                results = await to_thread(
                    reranker.__call__, query, limit, factor, **kwargs
                )

                self._rerankers.append(reranker)
            except Exception as e:
                log.error(e)

        return results
