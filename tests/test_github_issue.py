import unittest

from backend.ingestion.github_issue import parse_issue_ref


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


if __name__ == "__main__":
    unittest.main()
