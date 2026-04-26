import base64
import unittest
from unittest.mock import patch

from backend.ingestion.github_issue import GitHubError, create_fix_pr


class CreateFixPrTests(unittest.TestCase):
    def test_creates_branch_updates_file_and_opens_pr(self):
        calls = []

        def fake_github_json(method, path, payload=None):
            calls.append((method, path, payload))
            if method == "GET" and path == "/repos/owner/repo/git/ref/heads/main":
                return {"object": {"sha": "base-sha"}}
            if method == "GET" and path == "/repos/owner/repo/git/ref/heads/fix%2Fdemo":
                raise GitHubError("GitHub API GET failed with 404")
            if method == "POST" and path == "/repos/owner/repo/git/refs":
                return {"ref": "refs/heads/fix/demo"}
            if method == "GET" and path == "/repos/owner/repo/contents/auth%2Ftoken.go?ref=fix%2Fdemo":
                return {
                    "type": "file",
                    "sha": "file-sha",
                    "encoding": "base64",
                    "content": base64.b64encode(b"old").decode("ascii"),
                }
            if method == "PUT" and path == "/repos/owner/repo/contents/auth%2Ftoken.go":
                self.assertEqual(payload["branch"], "fix/demo")
                self.assertEqual(payload["sha"], "file-sha")
                return {"content": {"path": "auth/token.go"}}
            if method == "GET" and path.startswith("/repos/owner/repo/pulls?"):
                return []
            if method == "POST" and path == "/repos/owner/repo/pulls":
                return {"number": 2, "html_url": "https://example.test/pr/2", "state": "open"}
            raise AssertionError(f"unexpected call: {method} {path}")

        with patch("backend.ingestion.github_issue._github_json", side_effect=fake_github_json):
            result = create_fix_pr(
                "owner/repo",
                "fix/demo",
                {"auth/token.go": "new"},
                "Fix token cache race",
                "Adds locking.",
            )

        self.assertEqual(result["number"], 2)
        self.assertEqual(result["changed_paths"], ["auth/token.go"])
        self.assertIn(("POST", "/repos/owner/repo/git/refs", {"ref": "refs/heads/fix/demo", "sha": "base-sha"}), calls)


if __name__ == "__main__":
    unittest.main()
