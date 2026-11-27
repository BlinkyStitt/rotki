import copy
import io
import itertools
import json
import unittest

from ci_changes import changed_files
from rotki_changes import select
from rotki_gate import GROUPS, verify


class RotkiContractTests(unittest.TestCase):
    def test_component_and_rename_selection(self):
        self.assertEqual(
            select([{"filename": "docs/index.rst"}]),
            {
                "backend_tasks": False,
                "frontend_tasks": False,
                "documentation_tasks": True,
            },
        )
        self.assertEqual(
            select([{"filename": "frontend/app/a.ts"}]),
            {
                "backend_tasks": False,
                "frontend_tasks": True,
                "documentation_tasks": False,
            },
        )
        self.assertTrue(
            select([{"filename": "new.txt", "previous_filename": "rotkehlchen/a.py"}])[
                "backend_tasks"
            ]
        )

    def test_shared_and_unknown_changes_fail_closed(self):
        for path in [".github/workflows/rotki_ci.yml", "new-build-system.toml"]:
            self.assertTrue(all(select([{"filename": path}]).values()))

    def test_pagination_and_incomplete_response(self):
        pages = [[{"filename": str(n)} for n in range(100)], [{"filename": "last.py"}]]
        calls = []

        def opener(request, timeout):
            calls.append(request.full_url)
            return io.StringIO(json.dumps(pages.pop(0)))

        self.assertEqual(
            len(
                changed_files(
                    "https://api.github.com", "owner/repo", 2, 101, "token", opener
                )
            ),
            101,
        )
        self.assertIn("page=2", calls[-1])
        with self.assertRaises(ValueError):
            changed_files(
                "https://api.github.com",
                "owner/repo",
                2,
                1,
                "token",
                lambda *a, **k: io.StringIO("[]"),
            )

    def test_all_component_combinations(self):
        for flags in itertools.product([False, True], repeat=3):
            selected = dict(
                zip(["frontend_tasks", "backend_tasks", "documentation_tasks"], flags)
            )
            outputs = {name: str(value).lower() for name, value in selected.items()}
            selected["e2e"] = selected["frontend_tasks"] or selected["backend_tasks"]
            needs = {"check-changes": {"result": "success", "outputs": outputs}}
            needs.update(
                {
                    job: {"result": "success" if selected[group] else "skipped"}
                    for job, group in GROUPS.items()
                }
            )
            verify(needs)
            for job in GROUPS:
                for bad in [
                    "cancelled",
                    "failure",
                    "skipped" if selected[GROUPS[job]] else "success",
                ]:
                    altered = copy.deepcopy(needs)
                    altered[job]["result"] = bad
                    with self.assertRaises(ValueError):
                        verify(altered)
            for key in needs:
                altered = copy.deepcopy(needs)
                del altered[key]
                with self.assertRaises(ValueError):
                    verify(altered)

    def test_invalid_selector_results(self):
        needs = {job: {"result": "success"} for job in GROUPS}
        for selector in [{"result": "failure"}, {"result": "success", "outputs": {}}]:
            needs["check-changes"] = selector
            with self.assertRaises(ValueError):
                verify(needs)
