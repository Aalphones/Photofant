"""ONNX Session Manager — lazy load, idle unload, provider detection.

One SessionManager instance lives per process (singleton via module-level
`session_manager`).  Model adapters call `acquire_session` / `release_session`
to borrow an InferenceSession; the manager tracks idle time and evicts sessions
that have been unused longer than IDLE_TIMEOUT_SECONDS.
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import onnxruntime as ort

log = logging.getLogger(__name__)

IDLE_TIMEOUT_SECONDS: float = 300.0
_EXECUTOR_WORKERS: int = 1  # single-threaded: onnxruntime is not re-entrant per session


@dataclass
class _SessionEntry:
    session: ort.InferenceSession
    last_used: float = field(default_factory=time.monotonic)
    refcount: int = 0


class SessionManager:
    """Thread-safe cache of ONNX InferenceSessions with idle eviction."""

    def __init__(self, idle_timeout: float = IDLE_TIMEOUT_SECONDS) -> None:
        self._idle_timeout = idle_timeout
        self._lock = threading.Lock()
        self._sessions: dict[str, _SessionEntry] = {}
        self._executor = ThreadPoolExecutor(max_workers=_EXECUTOR_WORKERS, thread_name_prefix="ort-worker")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def acquire_session(self, model_path: str, provider_override: str | None = None) -> ort.InferenceSession:
        """Return a cached (or freshly loaded) InferenceSession for *model_path*.

        Raises RuntimeError if the session cannot be loaded (half-loaded state
        is never cached).  Call `release_session` when done.
        """
        with self._lock:
            entry = self._sessions.get(model_path)
            if entry is not None:
                entry.last_used = time.monotonic()
                entry.refcount += 1
                return entry.session

        # Load outside the lock so other models can still be acquired concurrently.
        session = self._load_session(model_path, provider_override)

        with self._lock:
            # Check again — another thread might have loaded the same model.
            if model_path not in self._sessions:
                self._sessions[model_path] = _SessionEntry(session=session, refcount=1)
            else:
                self._sessions[model_path].refcount += 1
            return self._sessions[model_path].session

    def release_session(self, model_path: str) -> None:
        """Decrement refcount; session is eligible for eviction once it hits 0."""
        with self._lock:
            entry = self._sessions.get(model_path)
            if entry is None:
                return
            entry.refcount = max(0, entry.refcount - 1)
            entry.last_used = time.monotonic()

    def evict_idle(self) -> None:
        """Evict sessions whose idle time exceeds the configured timeout.

        Intended to be called periodically (e.g. from a background task).
        Sessions with active references (refcount > 0) are never evicted.
        """
        now = time.monotonic()
        with self._lock:
            to_evict = [
                path
                for path, entry in self._sessions.items()
                if entry.refcount == 0 and (now - entry.last_used) > self._idle_timeout
            ]
            for path in to_evict:
                del self._sessions[path]
                log.info("Evicted idle ONNX session: %s", path)

    def evict_all(self) -> None:
        """Force-evict all sessions — called at shutdown."""
        with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
        if count:
            log.info("Evicted %d ONNX session(s) at shutdown", count)

    @property
    def executor(self) -> ThreadPoolExecutor:
        """Shared ThreadPoolExecutor for CPU-bound inference calls."""
        return self._executor

    # ------------------------------------------------------------------
    # Provider detection
    # ------------------------------------------------------------------

    @staticmethod
    def detect_providers(override: str | None = None) -> list[str]:
        """Return the ordered provider list for onnxruntime.

        Override values: 'cpu', 'cuda', 'directml'.
        Auto-detection order: DirectML → CUDA → CPU (broadest hardware coverage
        on Windows without requiring a CUDA toolkit install).
        """
        import onnxruntime as ort

        available = ort.get_available_providers()
        log.debug("Available ORT providers: %s", available)

        if override:
            canonical = {
                "cpu": "CPUExecutionProvider",
                "cuda": "CUDAExecutionProvider",
                "directml": "DmlExecutionProvider",
            }.get(override.lower())
            if canonical and canonical in available:
                log.info("ORT provider override: %s", canonical)
                return [canonical, "CPUExecutionProvider"]
            log.warning("Requested provider %r not available; falling back to auto-detect", override)

        for provider in ("DmlExecutionProvider", "CUDAExecutionProvider"):
            if provider in available:
                log.info("ORT provider auto-selected: %s", provider)
                return [provider, "CPUExecutionProvider"]

        log.info("ORT provider: CPUExecutionProvider (no GPU backend found)")
        return ["CPUExecutionProvider"]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_session(self, model_path: str, provider_override: str | None) -> ort.InferenceSession:
        import onnxruntime as ort

        path = Path(model_path)
        if not path.exists():
            raise RuntimeError(f"Model file not found: {model_path}")

        providers = self.detect_providers(provider_override)
        log.info("Loading ONNX session: %s (providers: %s)", path.name, providers)

        try:
            session = ort.InferenceSession(str(path), providers=providers)
        except Exception as error:
            raise RuntimeError(f"Failed to load ONNX model {path.name}: {error}") from error

        log.info("ONNX session ready: %s", path.name)
        return session

    def resolve_model_path(self, manifest_id: str, session_factory) -> str | None:
        """Look up the filesystem path for a manifest_id from the DB registry.

        Returns None when the model is disabled or has no path.
        Uses `session_factory` (callable → DB session context manager) to avoid
        a hard import cycle with photofant.db.
        """
        from photofant.db.models import ModelRegistry

        with session_factory() as db_session:
            entry = db_session.query(ModelRegistry).filter_by(
                manifest_id=manifest_id, enabled=True
            ).first()
            if entry is None:
                return None
            return entry.path


# Singleton — imported by adapters and job code.
session_manager = SessionManager()
