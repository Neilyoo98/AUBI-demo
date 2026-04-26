import unittest

from backend.ingestion.slack_integration import receive_slack_event


class SlackIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_relevant_message_returns_event(self):
        payload = {
            "event": {
                "type": "message",
                "text": "Auth endpoint is returning 401",
                "channel": "C123",
                "user": "U123",
                "ts": "1711111111.000100",
            }
        }

        event = await receive_slack_event(payload)

        self.assertEqual(
            event,
            {
                "text": "Auth endpoint is returning 401",
                "channel": "C123",
                "user": "U123",
                "ts": "1711111111.000100",
            },
        )

    async def test_irrelevant_message_returns_none(self):
        payload = {
            "event": {
                "type": "message",
                "text": "The queue drained successfully",
                "channel": "C123",
                "user": "U123",
                "ts": "1711111111.000100",
            }
        }

        self.assertIsNone(await receive_slack_event(payload))

    async def test_bot_message_returns_none(self):
        payload = {
            "event": {
                "type": "message",
                "subtype": "bot_message",
                "text": "auth 500",
                "channel": "C123",
                "user": "U123",
                "ts": "1711111111.000100",
            }
        }

        self.assertIsNone(await receive_slack_event(payload))


if __name__ == "__main__":
    unittest.main()
