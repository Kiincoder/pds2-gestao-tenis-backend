import hashlib
import unittest

from app.core.tokens import TokenService


class TokenServiceTests(unittest.TestCase):
    def setUp(self):
        self.tokens = TokenService()

    def test_generated_tokens_are_url_safe_and_distinct(self):
        first = self.tokens.issue()
        second = self.tokens.issue()
        self.assertTrue(self.tokens.is_well_formed(first))
        self.assertTrue(self.tokens.is_well_formed(second))
        self.assertNotEqual(first, second)

    def test_digest_is_sha256_and_does_not_contain_the_raw_token(self):
        token = self.tokens.issue()
        digest = self.tokens.digest(token)
        self.assertEqual(digest, hashlib.sha256(token.encode()).hexdigest())
        self.assertEqual(len(digest), 64)
        self.assertNotEqual(digest, token)

    def test_malformed_tokens_are_rejected(self):
        for token in ["", "short", "a" * 44, "a" * 42, "/" * 43, " " * 43, "á" * 43]:
            with self.subTest(token=token):
                self.assertFalse(self.tokens.is_well_formed(token))
