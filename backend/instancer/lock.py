from dataclasses import dataclass, field
from random import randbytes

from instancer.config import rclient


class LockException(Exception):
    """Exception thrown by Lock when the key to lock is already locked."""

    pass


@dataclass
class Lock:
    """Simple lock implemented using Redis."""

    name: str
    "The name of the lock."
    max_time: int = 60
    "The maximum time the lock can be locked."
    lock_value: str = field(default_factory=lambda: randbytes(8).hex())
    "The value stored in the lock. Used to determine if a lock should be released."

    def lock(self):
        if not rclient.set(
            "lock:" + self.name, self.lock_value, nx=True, ex=self.max_time
        ):
            raise LockException(f"Lock {self.name} already exists")

    def unlock(self):
        lock = "lock:" + self.name
        if rclient.get(lock) == self.lock_value.encode():
            rclient.delete(lock)

    def __enter__(self):
        self.lock()

    def __exit__(self, *args):
        self.unlock()
