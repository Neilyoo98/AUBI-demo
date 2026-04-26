import unittest
from unittest.mock import patch

from backend.ingestion.github_issue import get_latest_open_issue, parse_issue_ref


class GitHubIssueTests(unittest.TestCase):
    def test_parse_owner_repo_issue_ref(self):
        ref = parse_issue_ref("Neilyoo98/AUBI-demo#1")

        self.assertEqual(ref.repo, "Neilyoo98/AUBI-demo")
        self.assertEqual(ref.number, 1)

    def test_parse_github_issue_url(self):
        ref = parse_issue_ref("https://github.com/Neilyoo98/AUBI-demo/issues/12")

        self.assertEqual(ref.repo, "Neilyoo98/AUBI-demo")
        self.assertEqual(ref.number, 12)

    def test_rejects_invalid_refs(self):
        with self.assertRaises(ValueError):
            parse_issue_ref("Neilyoo98/AUBI-demo")

    def test_get_latest_open_issue_skips_pull_requests(self):
        with patch(
            "backend.ingestion.github_issue._github_json",
            return_value=[
                {"number": 2, "title": "PR", "pull_request": {}},
                {
                    "number": 1,
                    "title": "Authentication endpoint returning 401",
                    "body": "Blocking submissions",
                    "state": "open",
                    "user": {"login": "prof"},
                    "labels": [{"name": "bug"}],
                    "html_url": "https://github.com/owner/repo/issues/1",
                    "created_at": "2026-04-26T15:42:17Z",
                    "updated_at": "2026-04-26T15:42:17Z",
                },
            ],
        ):
            issue = get_latest_open_issue("owner/repo")

        self.assertEqual(issue["number"], 1)
        self.assertEqual(issue["title"], "Authentication endpoint returning 401")
        self.assertEqual(issue["labels"], ["bug"])


if __name__ == "__main__":
    unittest.main()
