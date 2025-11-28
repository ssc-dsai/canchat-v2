import threading
import uvicorn
from fastapi import FastAPI, Depends, Response
from typing import Optional
import inspect
import logging

from open_webui.metrics.base import MetricsInterface
from open_webui.metrics.exporters.in_memory import InMemoryMetrics

log = logging.getLogger(__name__)


class MetricsService:
    """
    A standalone FastAPI-based metrics server that runs in a
    background thread on its own port.

    Supports any MetricsInterface implementation:
      - InMemoryMetrics → JSON output
      - Prometheus exporter → /metrics exposes generate_latest()
    """

    def __init__(
        self,
        metrics_exporter: MetricsInterface = InMemoryMetrics,
        host: str = "0.0.0.0",
        port: int = 9000,
    ):
        # Instantiate exporter if class is passed
        if inspect.isclass(metrics_exporter):
            metrics_exporter = metrics_exporter()

        self.exporter: MetricsInterface = metrics_exporter or InMemoryMetrics()
        self.host = host
        self.port = port

        # FastAPI app for metrics
        self.app = self._setup_app()

        # Background thread handle
        self._thread: Optional[threading.Thread] = None

    def _setup_app(self) -> FastAPI:
        metrics_app = FastAPI()

        def get_exporter():
            return self.exporter

        @metrics_app.get("/metrics")
        def metrics_endpoint(metrics: MetricsInterface = Depends(get_exporter)):
            try:
                if hasattr(metrics, "get_content") and callable(getattr(metrics, "get_content")):
                    content, media_type = metrics.get_content()
                    return Response(content, media_type=media_type)
            except Exception as e:
                log.debug("metrics.get_content() failed: %s", e)

        return metrics_app

    def start(self):
        """Launch metrics FastAPI server in a separate daemon thread."""
        log.info(f"Starting Metrics Service on http://{self.host}:{self.port}")

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )

        server = uvicorn.Server(config)

        def _run():
            # blocking call — that's why it runs inside a thread
            server.run()

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        self._thread = thread
        return thread


    def get_exporter(self) -> MetricsInterface:
        return self.exporter
