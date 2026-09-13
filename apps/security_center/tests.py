from django.test import TestCase

from .utils import check_rate_limit


class SecurityThrottleTests(TestCase):
    def test_rate_limit_blocks_after_limit(self):
        for _ in range(3):
            allowed, _ = check_rate_limit(
                "test",
                "127.0.0.1",
                limit=3,
                window_seconds=60,
                block_seconds=60,
            )
            self.assertTrue(allowed)

        allowed, retry_after = check_rate_limit(
            "test",
            "127.0.0.1",
            limit=3,
            window_seconds=60,
            block_seconds=60,
        )

        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)
