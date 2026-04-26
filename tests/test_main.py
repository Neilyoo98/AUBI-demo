import unittest

from fastapi.testclient import TestClient

from backend.main import app


class MainEndpointTests(unittest.TestCase):
    def test_slack_url_verification(self):
        client = TestClient(app)

        response = client.post(
            "/slack/webhook",
            json={"type": "url_verification", "challenge": "challenge-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"challenge": "challenge-token"})

    def test_slack_webhook_ignores_irrelevant_message(self):
        client = TestClient(app)

        response = client.post(
            "/slack/webhook",
            json={
                "event": {
                    "type": "message",
                    "text": "queue drained",
                    "channel": "C123",
                    "user": "U123",
                    "ts": "1711111111.000100",
                }
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})


if __name__ == "__main__":
    unittest.main()
