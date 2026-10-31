"""The CI jobs have every command they run (erro 7: what the pipeline needs must exist in its image).

Both jobs (Forgejo and GitHub) run in node:22-bookworm-slim (Debian 12 slim + Node.js) plus the
apt-get list of their workflow. Every command a step starts, and every command `make tools` checks,
must come from that image or from a package of the list. The GitHub workflow is a copy of the Forgejo
one: only the checkout and the release step may differ, and every action is pinned to a commit.
"""

import pathlib
import re
import shlex
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FORGEJO = ROOT / ".forgejo" / "workflows" / "build.yaml"
GITHUB = ROOT / ".github" / "workflows" / "build.yaml"
WORKFLOWS = (FORGEJO, GITHUB)
MAKEFILE = ROOT / "Makefile"
# In node:22-bookworm-slim without installing anything: Node.js, dash and coreutils.
IMAGE = {"node", "npm", "sh", "cd", "rm", "timeout", "sha256sum", "apt-get", "for", "do", "done", "command"}
# Command (or Python module) → Debian 12 package that provides it.
PACKAGES = {
    "make": "make",
    "python3": "python3",
    "git": "git",
    "fc-list": "fontconfig",
    "pyflakes": "python3-pyflakes",
    "weasyprint": "weasyprint",
}


def apt_packages(workflow=FORGEJO):
    text = workflow.read_text(encoding="utf-8")
    install = re.search(r"apt-get install((?:.*\\\n)*.*)", text)[1]
    return {word for word in install.split() if not word.startswith("-") and word != "\\"}


def run_blocks(workflow):
    """The text of every run: block of the workflow, in order."""
    found = re.findall(r"run: (?:\|\n((?:\s{10,}.*\n)+)|(.*))", workflow.read_text(encoding="utf-8"))
    return [block[0] or block[1] for block in found]


def step_commands(workflow=FORGEJO):
    """First word of every shell command in the run: blocks of the workflow."""
    found = set()
    for block in run_blocks(workflow):
        for line in block.replace("\\\n", " ").splitlines():
            line = line.split("#")[0].strip()
            for command in re.split(r"&&|\|\||;", line):
                words = shlex.split(command)
                if words and words[0] != "timeout":
                    found.add(words[0])
                elif len(words) > 2:
                    found.add(words[2])  # timeout 30m <command>
    return found


class CiImage(unittest.TestCase):
    def test_every_step_command_is_in_the_image_or_installed(self):
        for workflow in WORKFLOWS:
            installed = apt_packages(workflow)
            for command in step_commands(workflow):
                if command.startswith(("dist/", "./")) or command in IMAGE:
                    continue
                with self.subTest(workflow=workflow.parent.parent.name, command=command):
                    self.assertIn(PACKAGES.get(command, command), installed, f"{command} is not in the CI image")

    def test_github_runs_the_forgejo_steps_and_only_its_own_release(self):
        forgejo, github = run_blocks(FORGEJO), run_blocks(GITHUB)
        self.assertEqual(github[:-1], forgejo[:-1], "same image, tools, tests and build on both forges")
        self.assertEqual(
            (forgejo[-1], github[-1]), ("python3 -B scripts/forgejo_release.py", "python3 -B scripts/github_release.py")
        )
        for workflow in WORKFLOWS:
            text = workflow.read_text(encoding="utf-8")
            with self.subTest(workflow=workflow.parent.parent.name):
                self.assertIn("image: node:22-bookworm-slim", text)
                self.assertRegex(text, r"tags:\n\s+- 'v\*'", "only a version tag starts a run")
                for action in re.findall(r"uses: (\S+)", text):
                    self.assertRegex(action, r"@[0-9a-f]{40}$", "actions are pinned to a commit")
                self.assertIn("persist-credentials: false", text)
        github_text = GITHUB.read_text(encoding="utf-8")
        self.assertIn("permissions: {}", github_text, "no token permission unless the job asks")
        self.assertEqual(
            re.findall(r"^\s+(\w[\w-]*): write", github_text, re.M), ["contents"], "write only to contents"
        )

    def test_every_tool_that_make_tools_checks_is_installed(self):
        tools = re.search(r"^tools:\n((?:\t.*\n)+)", MAKEFILE.read_text(encoding="utf-8"), re.M)[1]
        commands = set(re.search(r"for c in ([^;]+); do", tools)[1].replace("$(PYTHON)", "python3").split())
        modules = set(re.findall(r"import (\w+)", tools))
        installed = apt_packages()
        for name in commands | modules:
            if name in IMAGE:
                continue
            with self.subTest(name=name):
                self.assertIn(PACKAGES.get(name, name), installed, f"make tools needs {name}, not in the CI image")
        self.assertIn("fonts-noto-cjk", installed, "the manual needs a CJK font")


if __name__ == "__main__":
    unittest.main()
