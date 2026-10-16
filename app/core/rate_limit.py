import math
import time
from collections import deque
from collections.abc import Callable
from threading import Lock


class RegistrationRateLimiter:
    """Janela deslizante por IP; memória local de um único processo."""

    def __init__(
        self,
        limit: int = 5,
        window_seconds: int = 60,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if limit < 1 or window_seconds < 1:
            raise ValueError("Limite e janela devem ser positivos.")
        self.limit = limit
        self.window = window_seconds
        self.clock = clock
        self.attempts: dict[str, deque[float]] = {}
        self.lock = Lock()

    def check(self, client_ip: str) -> int | None:
        with self.lock:
            now = self.clock()
            expired = [
                key for key, values in self.attempts.items() if values[-1] <= now - self.window
            ]
            for key in expired:
                del self.attempts[key]
            attempts = self.attempts.setdefault(client_ip, deque())
            while attempts and attempts[0] <= now - self.window:
                attempts.popleft()
            if len(attempts) >= self.limit:
                return max(1, math.ceil(attempts[0] + self.window - now))
            attempts.append(now)
            return None
