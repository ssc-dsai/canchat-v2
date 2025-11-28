from typing import Protocol, Dict, Optional, Iterable, Any, Tuple
from contextlib import contextmanager
from pydantic import BaseModel


class Labels(BaseModel):
    labels: Dict[str, str]  # Correctly define the Labels class


class MetricsInterface(Protocol):
    # Counter
    def counter(self, name: str, labels: Optional[Iterable[str]] = None) -> Any:
        """Ensure a counter exists and return a handle to increment it."""

    # Gauge
    def gauge(self, name: str, labels: Optional[Iterable[str]] = None) -> Any:
        """Ensure a gauge exists and return a handle to set it."""

    # Histogram
    def histogram(self, name: str, labels: Optional[Iterable[str]] = None) -> Any:
        """Ensure a histogram exists and return a handle to record durations."""

    # Timer context manager
    @contextmanager
    def timer(self, name: str, labels: Optional[Iterable[str]] = None, label_values: Optional[Labels] = None) -> Any:
        """Context manager that times a block of code."""

    # Get values
    def get_values(self) -> Dict[str, Dict[str, Any]]:
        """Return a snapshot of recorded metrics."""

    # Get content for export
    def get_content(self) -> Tuple[bytes, str]:
        """Return (bytes_content, media_type) tuple for metrics export."""