import unittest
from concurrent.futures import ThreadPoolExecutor

from app.core.rate_limit import RegistrationRateLimiter


class RegistrationRateLimiterTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.limiter = RegistrationRateLimiter(clock=lambda: self.now)

    def test_sixth_attempt_is_blocked_with_retry_after(self):
        for _ in range(5):
            self.assertIsNone(self.limiter.check("127.0.0.1"))
        self.assertEqual(self.limiter.check("127.0.0.1"), 60)

    def test_other_ip_has_an_independent_limit(self):
        for _ in range(5):
            self.limiter.check("127.0.0.1")
        self.assertIsNone(self.limiter.check("127.0.0.2"))

    def test_expired_attempts_allow_registration_again(self):
        for _ in range(5):
            self.limiter.check("127.0.0.1")
        self.now += 60
        self.assertIsNone(self.limiter.check("127.0.0.1"))

    def test_sliding_window_uses_oldest_attempt_and_rounds_up(self):
        self.limiter.check("127.0.0.1")
        self.now += 10
        for _ in range(4):
            self.limiter.check("127.0.0.1")
        self.now += 0.5
        self.assertEqual(self.limiter.check("127.0.0.1"), 50)
        self.now = 160
        self.assertIsNone(self.limiter.check("127.0.0.1"))
        self.assertEqual(self.limiter.check("127.0.0.1"), 10)

    def test_concurrent_requests_cannot_exceed_limit(self):
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(self.limiter.check, ["127.0.0.1"] * 20))
        self.assertEqual(results.count(None), 5)

    def test_invalid_limits_are_rejected(self):
        for limit, window in [(0, 60), (5, 0), (-1, 60)]:
            with self.subTest(limit=limit, window=window), self.assertRaises(ValueError):
                RegistrationRateLimiter(limit=limit, window_seconds=window)
