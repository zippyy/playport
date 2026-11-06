# SPDX-License-Identifier: GPL-3.0-or-later
"""Fail-closed public CI regression policy, using only the Python standard library.

Approve each entire executable workflow, not an upload-command/suffix denylist.
New jobs/actions/scripts/permissions must be reviewed here as well as in YAML.
checks.yml tests the source; pages.yml publishes site/ (the landing page).
forever-ipa.yml is a manually triggered, unsigned artifact-only build and never signs
with credentials, installs on a device or publishes a release.
This cannot defend against changes to this test or uploads hidden in tested code.
"""

from pathlib import Path
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
CHECKOUT = "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"
# v4.2.2 commit confirmed through the actions/checkout GitHub tag-ref API.
# Deliberately duplicate the approved policy rather than derive it from the
# workflow under test. No YAML parser dependency or permissive unknown fields.
APPROVED_CHECKS = """name: checks
on:
  push:
  pull_request:
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
        with:
          persist-credentials: false
      - name: Source-only workflow policy
        run: python3 -m unittest discover -v -s tools/tests -p test_release_ci.py
      - name: Allow ThreadSanitizer
        run: sudo sysctl vm.mmap_rnd_bits=28
      - name: pp test --quick (the name gate, secrets, pin and patch series, tools/tests, the host C tests)
        run: ./pp test --quick
  licence:
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
        with:
          persist-credentials: false
      - name: Converter exception adopted
        run: |
          grep -q '^Adopted on: [0-9]' LICENSE-EXCEPTION.md
"""

APPROVED_PAGES = """name: pages
on:
  push:
    branches: [main]
    paths: [site/**, .github/workflows/pages.yml]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
      - uses: actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9 # v5.0.0
        with:
          path: site
      - id: deploy
        uses: actions/deploy-pages@368f82528645a54fb793d4d04e342629a3f51346 # v5.0.1
"""
APPROVED_FOREVER = "# SPDX-License-Identifier: GPL-3.0-or-later\n# Manual, unsigned IPA build. No Apple account or signing certificate is needed.\n# Required repository secrets: PLAYPORT_SDK_ARCHIVE_URL, PLAYPORT_SDK_SHA256,\n# PLAYPORT_MINGW_ARCHIVE_URL, PLAYPORT_MINGW_SHA256.\n# The SDK archive must contain the xtool Darwin SDK tree (Developer/Toolchains/...,\n# Platforms/iPhoneOS.platform/... and Platforms/MacOSX.platform/...).\n# The mingw archive must contain the llvm-mingw 20260922 toolchain already patched\n# with the arm64ec CRT rebuild described in docs/BUILDING.md.\nname: Playport Forever unsigned IPA\non:\n  workflow_dispatch:\npermissions:\n  contents: read\nconcurrency:\n  group: playport-forever-ipa\n  cancel-in-progress: false\njobs:\n  build:\n    runs-on: ubuntu-24.04\n    timeout-minutes: 360\n    env:\n      PLAYPORT_SDK_ARCHIVE_URL: ${{ secrets.PLAYPORT_SDK_ARCHIVE_URL }}\n      PLAYPORT_SDK_SHA256: ${{ secrets.PLAYPORT_SDK_SHA256 }}\n      PLAYPORT_MINGW_ARCHIVE_URL: ${{ secrets.PLAYPORT_MINGW_ARCHIVE_URL }}\n      PLAYPORT_MINGW_SHA256: ${{ secrets.PLAYPORT_MINGW_SHA256 }}\n      JOBS: \"4\"\n    steps:\n      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2\n        with:\n          persist-credentials: false\n          submodules: recursive\n      - name: Ensure the build inputs are configured\n        shell: bash\n        run: |\n          set -euo pipefail\n          for key in PLAYPORT_SDK_ARCHIVE_URL PLAYPORT_SDK_SHA256 PLAYPORT_MINGW_ARCHIVE_URL PLAYPORT_MINGW_SHA256; do\n            if [ -z \"${!key}\" ]; then\n              echo \"::error::Missing ${key} repository secret. See docs/BUILDING.md; GitHub runners do not ship Apple's iOS SDK or Playport's patched MinGW.\"\n              exit 1\n            fi\n          done\n      - name: Free runner space and install host prerequisites\n        shell: bash\n        run: |\n          set -euo pipefail\n          df -h .\n          sudo rm -rf /usr/local/lib/android /opt/hostedtoolcache /usr/share/dotnet /usr/local/share/powershell\n          sudo apt-get update\n          sudo apt-get install -y --no-install-recommends build-essential bison flex gettext cmake ninja-build meson python3-pefile xxd openssl patch git rsync p7zip-full curl jq libssl-dev libxml2-dev\n          df -h .\n      - name: Unpack checksum-verified build inputs\n        shell: bash\n        run: |\n          set -euo pipefail\n          mkdir -p .work/inputs/darwin-sdk .work/inputs/llvm-mingw .work/downloads\n          curl --fail --location --retry 3 --output .work/downloads/sdk.tar.gz \"$PLAYPORT_SDK_ARCHIVE_URL\"\n          echo \"$PLAYPORT_SDK_SHA256  .work/downloads/sdk.tar.gz\" | sha256sum -c -\n          tar -xzf .work/downloads/sdk.tar.gz -C .work/inputs/darwin-sdk\n          curl --fail --location --retry 3 --output .work/downloads/mingw.tar.gz \"$PLAYPORT_MINGW_ARCHIVE_URL\"\n          echo \"$PLAYPORT_MINGW_SHA256  .work/downloads/mingw.tar.gz\" | sha256sum -c -\n          tar -xzf .work/downloads/mingw.tar.gz -C .work/inputs/llvm-mingw\n          rm -f .work/downloads/*.tar.gz\n          test -e .work/inputs/llvm-mingw/aarch64-w64-mingw32/lib/libgcc.a\n          test -x .work/inputs/llvm-mingw/bin/aarch64-w64-mingw32-clang\n      - name: Verify Linux toolchain requirements\n        shell: bash\n        run: |\n          set -euo pipefail\n          for cmd in clang clang++ ld64.lld llvm-ar llvm-nm llvm-objdump llvm-objcopy llvm-lipo swift; do\n            command -v \"$cmd\" >/dev/null || { echo \"::error::Missing $cmd. Install the LLVM 22 and Swift toolchains specified in docs/BUILDING.md on the build runner.\"; exit 1; }\n          done\n          if ! clang --version | head -1 | grep -Eq 'version 22\\.'; then\n            echo \"::error::This build requires host LLVM 22.x (docs/BUILDING.md).\"\n            exit 1\n          fi\n      - name: Build unsigned release IPA\n        shell: bash\n        env:\n          LLVM_MINGW: ${{ github.workspace }}/.work/inputs/llvm-mingw\n          DARWIN_SDK: ${{ github.workspace }}/.work/inputs/darwin-sdk\n        run: |\n          set -euo pipefail\n          ./pp setup\n          ./pp build --variant release --unsigned\n          find .work/out -name '*release-unsigned-*.ipa' -type f -print\n      - name: Collect verified IPA\n        shell: bash\n        run: |\n          set -euo pipefail\n          mkdir -p .work/upload\n          mapfile -t ipa < <(find .work/out -name '*release-unsigned-*.ipa' -type f)\n          test \"${#ipa[@]}\" -eq 1 || { echo \"::error::Expected exactly one verified unsigned IPA\"; exit 1; }\n          cp \"${ipa[0]}\" .work/upload/Playport-Forever-unsigned.ipa\n          sha256sum .work/upload/*.ipa > .work/upload/SHA256SUMS\n      - name: Upload unsigned IPA\n        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2\n        with:\n          name: Playport-Forever-unsigned-IPA\n          path: .work/upload/\n          if-no-files-found: error\n          retention-days: 7\n"
APPROVED = {"checks.yml": APPROVED_CHECKS, "pages.yml": APPROVED_PAGES, "forever-ipa.yml": APPROVED_FOREVER}


def executable_lines(text):
    """Only full-line comments and blank lines may change without review."""
    return [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def workflow_problems(directory):
    """Check the complete workflow directory, including untracked new workflows."""
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        return ["workflow directory must be a regular directory"]
    entries = sorted(directory.iterdir())
    if [entry.name for entry in entries] != sorted(APPROVED):
        return ["only the reviewed checks.yml, pages.yml and forever-ipa.yml workflows are allowed"]
    for workflow in entries:
        name = workflow.name
        if workflow.is_symlink() or not workflow.is_file():
            return [f"{name} must be a regular file"]
        try:
            text = workflow.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return [f"{name} must be readable UTF-8"]
        if executable_lines(text) != executable_lines(APPROVED[name]):
            return [f"{name} differs from the reviewed policy"]
    return []


class PublicCI(unittest.TestCase):
    def test_repository_workflows_match_approved_policies(self):
        self.assertEqual(workflow_problems(REPO / ".github/workflows"), [])


class PolicyRegressions(unittest.TestCase):
    def setUp(self):
        scratch = REPO / ".work/release-ci-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "workflows"
        self.directory.mkdir()
        self.workflow = self.directory / "checks.yml"
        self.workflow.write_text(APPROVED_CHECKS, encoding="utf-8")
        self.pages = self.directory / "pages.yml"
        self.pages.write_text(APPROVED_PAGES, encoding="utf-8")
        self.forever = self.directory / "forever-ipa.yml"
        self.forever.write_text(APPROVED_FOREVER, encoding="utf-8")

    def reject(self, text):
        self.workflow.write_text(text, encoding="utf-8")
        self.assertTrue(workflow_problems(self.directory))

    def test_approved_workflow_and_full_line_comments(self):
        self.assertEqual(workflow_problems(self.directory), [])
        self.workflow.write_text("# explanation\n\n" + APPROVED_CHECKS + "\n# end\n", encoding="utf-8")
        self.assertEqual(workflow_problems(self.directory), [])

    def test_any_artifact_or_cache_upload_is_rejected(self):
        for action in ("actions/upload-artifact@v4", "actions/cache@v4", "vendor/publish@v1"):
            for payload in ("*.ipa", ".work/out", "signed-app.zip", "source.tar.gz"):
                with self.subTest(action=action, payload=payload):
                    self.reject(APPROVED_CHECKS + f"      - uses: {action}\n"
                                f"        with:\n          path: {payload}\n")

    def test_shell_build_sign_install_and_upload_are_rejected(self):
        for command in ("./pp build", "./pp check", "./pp install", "xtool dev build --ipa",
                        "gh release upload v1 signed-app.zip", "curl -T signed-app.zip https://example.invalid",
                        "python3 publish.py", "./pp test --quick; ./pp build",
                        "./pp test --quick\n          ./pp build"):
            with self.subTest(command=command):
                self.reject(APPROVED_CHECKS.replace("run: ./pp test --quick", f"run: {command}"))

    def test_actions_containers_and_reusable_workflows_are_rejected(self):
        for action in ("./.github/actions/publish", "vendor/build@v1", "docker://publisher:latest",
                       "actions/checkout@v4"):
            with self.subTest(action=action):
                self.reject(APPROVED_CHECKS.replace(CHECKOUT, action))
        self.reject(APPROVED_CHECKS + "  publish:\n    uses: vendor/repo/.github/workflows/build.yml@main\n")
        self.reject(APPROVED_CHECKS.replace("    timeout-minutes: 15", "    container: vendor/builder\n    timeout-minutes: 15"))

    def test_credentials_permissions_and_runner_changes_are_rejected(self):
        changes = (
            ("contents: read", "contents: write"),
            ("contents: read", "contents: read\n  id-token: write"),
            ("persist-credentials: false", "persist-credentials: true"),
            ("persist-credentials: false", "persist-credentials: false\n          token: ${{ secrets.SIGNING_TOKEN }}"),
            ("jobs:", "env:\n  SIGNING_KEY: ${{ secrets.SIGNING_KEY }}\njobs:"),
            ("runs-on: ubuntu-24.04", "runs-on: self-hosted"),
            ("  pull_request:", "  pull_request_target:"),
            ("  pull_request:", "  pull_request:\n  workflow_run:"),
            ("permissions:\n  contents: read\n", ""),
        )
        for old, new in changes:
            with self.subTest(change=new):
                self.reject(APPROVED_CHECKS.replace(old, new))

    def test_policy_step_removal_and_yaml_indirection_are_rejected(self):
        self.reject(APPROVED_CHECKS.replace(
            "      - name: Source-only workflow policy\n"
            "        run: python3 -m unittest discover -v -s tools/tests -p test_release_ci.py\n", ""))
        for extra in ("---\n" + APPROVED_CHECKS, "jobs: {}\n", "env: &upload {CMD: publish}\n",
                      "defaults:\n  run:\n    shell: python\n"):
            with self.subTest(extra=extra):
                self.reject(APPROVED_CHECKS + extra)

    def test_pages_publishes_only_the_site(self):
        changes = (
            ("path: site", "path: ."),
            ("path: site", "path: .work/out"),
            ("contents: read", "contents: write"),
            ("    paths: [site/**, .github/workflows/pages.yml]\n", ""),
            ("runs-on: ubuntu-latest", "runs-on: self-hosted"),
            ("      - id: deploy", "      - run: ./pp build\n      - id: deploy"),
        )
        for old, new in changes:
            with self.subTest(change=new):
                self.assertIn(old, APPROVED_PAGES)
                self.pages.write_text(APPROVED_PAGES.replace(old, new), encoding="utf-8")
                self.assertTrue(workflow_problems(self.directory))
        self.pages.unlink()
        self.assertTrue(workflow_problems(self.directory))

    def test_forever_build_is_manual_and_does_not_use_signing_credentials(self):
        self.assertIn("  workflow_dispatch:", APPROVED_FOREVER)
        self.assertNotIn("  push:", APPROVED_FOREVER)
        self.assertNotIn("  pull_request:", APPROVED_FOREVER)
        self.assertIn("./pp build --variant release --unsigned", APPROVED_FOREVER)
        self.assertNotIn("secrets.SIGNING", APPROVED_FOREVER)
        self.forever.write_text(APPROVED_FOREVER.replace("--unsigned", "--sign"), encoding="utf-8")
        self.assertTrue(workflow_problems(self.directory))
        self.forever.write_text(APPROVED_FOREVER, encoding="utf-8")

    def test_new_or_renamed_workflows_and_nested_entries_are_rejected(self):
        for name in ("release.yml", "publish.yaml", "checks.yaml", "hidden.txt"):
            with self.subTest(name=name):
                entry = self.directory / name
                entry.write_text(APPROVED_CHECKS, encoding="utf-8")
                self.assertTrue(workflow_problems(self.directory))
                entry.unlink()
        (self.directory / "nested").mkdir()
        self.assertTrue(workflow_problems(self.directory))

    def test_missing_symlink_directory_and_unreadable_text_are_rejected(self):
        self.workflow.unlink()
        self.assertTrue(workflow_problems(self.directory))
        self.workflow.mkdir()
        self.assertTrue(workflow_problems(self.directory))
        self.workflow.rmdir()
        target = self.directory.parent / "target.yml"
        target.write_text(APPROVED_CHECKS, encoding="utf-8")
        self.workflow.symlink_to(target)
        self.assertTrue(workflow_problems(self.directory))
        self.workflow.unlink()
        self.workflow.write_bytes(b"\xff")
        self.assertTrue(workflow_problems(self.directory))
        link = self.directory.parent / "linked-workflows"
        link.symlink_to(self.directory, target_is_directory=True)
        self.assertTrue(workflow_problems(link))
        self.assertTrue(workflow_problems(self.directory.parent / "missing"))


if __name__ == "__main__":
    unittest.main()
