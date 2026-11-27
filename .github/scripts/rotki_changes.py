"""Select component validation from the complete pull-request diff."""

import json
import os

from ci_changes import changed_files, needs_validation

PATTERNS = {
    "backend_tasks": [
        "rotkehlchen/**",
        "requirements*.txt",
        "setup.py",
        "setup.cfg",
        "pyproject.toml",
        "Makefile",
        "pytestgeventwrapper.py",
        "install_deps.sh",
    ],
    "frontend_tasks": ["frontend/**", "package*.json", "yarn.lock"],
    "documentation_tasks": [
        "docs/**",
        "requirements_docs.txt",
        "rotkehlchen/**",
        "setup.py",
        "setup.cfg",
        "README*",
        "CHANGELOG*",
    ],
}


def select(files):
    decisions = {
        name: needs_validation(files, patterns, [])
        for name, patterns in PATTERNS.items()
    }
    # Unknown build impact must not silently omit validation.
    for entry in files:
        for path in [entry["filename"], entry.get("previous_filename")]:
            if path and not any(
                needs_validation([{"filename": path}], patterns, [])
                for patterns in PATTERNS.values()
            ):
                return dict.fromkeys(PATTERNS, True)
    return decisions


def main():
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as stream:
        event = json.load(stream)
    count = event["pull_request"]["changed_files"]
    decisions = dict.fromkeys(PATTERNS, True)
    if count < 3000:
        files = changed_files(
            os.environ["GITHUB_API_URL"],
            os.environ["GITHUB_REPOSITORY"],
            event["number"],
            count,
            os.environ["GH_TOKEN"],
        )
        decisions = select(files)
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
        for name, value in decisions.items():
            stream.write(name + "=" + str(value).lower() + "\n")


if __name__ == "__main__":
    main()
