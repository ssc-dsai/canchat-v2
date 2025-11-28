# No-operation implementation of MetricsInterface for testing
from contextlib import contextmanager
from open_webui.metrics.base import MetricsInterface
import time
import json

# No-operation Metrics implementation for testing or when metrics are disabled
class InMemoryMetrics(MetricsInterface):
    def __init__(self):
        self._counters = {}
        self._gauges = {}
        self._histograms = {}

    def _label_key(self, labels):
        if labels is None:
            return None
        if isinstance(labels, dict):
            return tuple(sorted(labels.items()))
        try:
            return tuple(labels)
        except Exception:
            return repr(labels)

    def _make_key(self, name, labels):
        """Create a string key from name and labels"""
        label_key = self._label_key(labels)
        if label_key is None:
            return name
        return f"{name}:{label_key}"

    def counter(self, name, labels=None):
        key = self._make_key(name, labels)
        class C:
            def __init__(self, parent, key):
                self._parent = parent
                self._key = key
            def inc(self, value=1, *_args, **_kwargs):
                self._parent._counters[self._key] = self._parent._counters.get(self._key, 0) + value
        return C(self, key)

    def gauge(self, name, labels=None):
        key = self._make_key(name, labels)
        class G:
            def __init__(self, parent, key):
                self._parent = parent
                self._key = key
            def set(self, value, *_args, **_kwargs):
                self._parent._gauges[self._key] = value
        return G(self, key)

    def histogram(self, name, labels=None):
        key = self._make_key(name, labels)
        class H:
            def __init__(self, parent, key):
                self._parent = parent
                self._key = key
            def observe(self, value, *_args, **_kwargs):
                self._parent._histograms.setdefault(self._key, []).append(value)
        return H(self, key)

    @contextmanager
    def timer(self, name, labels=None, label_values=None):
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            key = self._make_key(name, labels)
            self._histograms.setdefault(key, []).append(duration)

    def get_values(self):
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {k: list(v) for k, v in self._histograms.items()},
        }

    def get_content(self):
        """Return (bytes_content, media_type) for the metrics snapshot."""
        payload = json.dumps(self.get_values(), default=str).encode("utf-8")
        return payload, "application/json"