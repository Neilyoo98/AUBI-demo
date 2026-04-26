import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app


class MainEndpointTests(unittest.TestCase):
    def test_health(self):
        client = TestClient(app)

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

    @patch("backend.main.get_latest_open_issue")
    @patch.dict("os.environ", {"DEMO_REPO": "owner/repo"})
    def test_github_poll_returns_latest_issue(self, get_latest_open_issue):
        get_latest_open_issue.return_value = {"number": 1, "title": "Auth 401"}
        client = TestClient(app)

        response = client.get("/github/poll")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"issue": {"number": 1, "title": "Auth 401"}})
        get_latest_open_issue.assert_called_once_with("owner/repo")


if __name__ == "__main__":
    unittest.main()
