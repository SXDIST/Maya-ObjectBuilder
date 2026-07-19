"""Interruptible progress reporting for the long import/export loops.

``MComputation`` exists only in the API 1.0 Python bindings — ``maya.api.OpenMaya`` has no
equivalent, despite the C++ header being right there in the devkit. It is therefore imported
from ``maya.OpenMaya``, the same split the file translator already lives with.

Everything degrades to a no-op when the class or a progress bar is unavailable (batch mode,
mayapy, a future API change): a missing progress indicator must never be the reason an export
fails.
"""


class Progress:
    """Context manager wrapping one interruptible loop.

    Usage::

        with Progress(len(items)) as progress:
            for index, item in enumerate(items):
                if progress.cancelled():
                    ...
                    break
                do_work(item)
                progress.step(index + 1)
    """

    def __init__(self, total):
        self._total = max(int(total), 0)
        self._computation = None

    def __enter__(self):
        try:
            import maya.OpenMaya as om1  # API 1.0: MComputation is not in API 2.0
            self._computation = om1.MComputation()
            self._computation.beginComputation(True, True, False)
            self._computation.setProgressRange(0, self._total)
        except Exception:  # noqa: BLE001 - no progress bar is not an error
            self._computation = None
        return self

    def __exit__(self, *_exc):
        if self._computation is not None:
            try:
                self._computation.endComputation()
            except Exception:  # noqa: BLE001
                pass
            self._computation = None
        return False

    def cancelled(self):
        """True once the user has pressed Esc."""
        if self._computation is None:
            return False
        try:
            return bool(self._computation.isInterruptRequested())
        except Exception:  # noqa: BLE001
            return False

    def step(self, done):
        if self._computation is None:
            return
        try:
            self._computation.setProgress(int(done))
        except Exception:  # noqa: BLE001
            pass


__all__ = ["Progress"]
