"""Account for selected, missing, cancelled, and skipped native validation."""

import json
import os

GROUPS = {
    "check-frontend": "frontend_tasks",
    "docs": "documentation_tasks",
    "lint-backend": "backend_tasks",
    "test-backend": "backend_tasks",
    "test-e2e": "e2e",
}


def verify(needs):
    if set(needs) != set(GROUPS) | {"check-changes"}:
        raise ValueError("Missing or unexpected validation jobs")
    selector = needs["check-changes"]
    if selector["result"] != "success":
        raise ValueError("Changed-file selection failed")
    outputs = selector.get("outputs", {})
    names = ["frontend_tasks", "backend_tasks", "documentation_tasks"]
    if any(outputs.get(name) not in ["true", "false"] for name in names):
        raise ValueError("Invalid component selection")
    selected = {name: outputs[name] == "true" for name in names}
    selected["e2e"] = selected["frontend_tasks"] or selected["backend_tasks"]
    for job, group in GROUPS.items():
        expected = "success" if selected[group] else "skipped"
        if needs[job]["result"] != expected:
            raise ValueError(job + ": " + needs[job]["result"])


if __name__ == "__main__":
    verify(json.loads(os.environ["CI_GATE_NEEDS"]))
