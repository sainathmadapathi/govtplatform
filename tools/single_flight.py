"""One in-flight call per key, its result shared by everyone who asked while it ran.

Used where many requests can ask for the same slow thing at once -- a probe of the Claude CLI, a fetch
of an upstream feed. The first caller for a key runs the call; callers that arrive while it runs wait
for it and receive the same outcome: its result, or the exception it raised. A failure is therefore
shared, not retried by each waiter in turn (which turned one failed 30 s probe into several in a row).

Nothing is remembered once the call completes: the next caller for that key starts a new one, so a
failure is never cached here and recovery is never blocked. Callers that want a result kept (or a
failure backed off) do that themselves, outside this helper.
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Hashable


class _Flight:
    __slots__ = ('done', 'result', 'error')

    def __init__(self) -> None:
        self.done = threading.Event()
        self.result: Any = None
        self.error: BaseException | None = None


class SingleFlight:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._flights: dict = {}

    def do(self, key: Hashable, fn: Callable[[], Any]) -> Any:
        """Run `fn` for `key`, or wait for the run already in flight and share its outcome."""
        with self._lock:
            flight = self._flights.get(key)
            leader = flight is None
            if leader:
                flight = self._flights[key] = _Flight()
        if not leader:
            flight.done.wait()
            if flight.error is not None:
                raise flight.error
            return flight.result
        try:
            flight.result = fn()
            return flight.result
        except BaseException as exc:                          # noqa: BLE001 -- shared, then re-raised
            flight.error = exc
            raise
        finally:
            with self._lock:
                self._flights.pop(key, None)
            flight.done.set()

    def in_flight(self, key: Hashable) -> bool:
        with self._lock:
            return key in self._flights
