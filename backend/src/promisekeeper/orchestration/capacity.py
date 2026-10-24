"""One process-wide Investigator reservation, acquired before a durable start."""

from threading import Condition
from time import monotonic


class Capacity:
    def __init__(self):
        self._condition = Condition()
        self._owner = None
        self._starting = False

    @property
    def available(self):
        with self._condition:
            return self._owner is None

    def reserve(self, owner):
        with self._condition:
            if self._owner is not None:
                return False
            self._owner, self._starting = owner, True
            return True

    def persisted(self, owner):
        with self._condition:
            if self._owner == owner:
                self._starting = False
                self._condition.notify_all()

    def await_start(self):
        # Let a concurrent durable start publish its receipt before busy/replay lookup.
        with self._condition:
            until = monotonic() + 0.3
            while self._starting and monotonic() < until:
                self._condition.wait(max(0, until - monotonic()))

    def release(self, owner):
        with self._condition:
            if self._owner == owner:
                self._owner, self._starting = None, False
                self._condition.notify_all()


PROCESS_CAPACITY = Capacity()
