# Building the Forever IPA with GitHub Actions

The manual [Playport Forever unsigned IPA](../.github/workflows/forever-ipa.yml) workflow
builds the **release** variant using `./pp build --variant release --unsigned`.
It uploads an unsigned IPA artifact, never an Apple signing key or profile.
The main app's bundle ID is `xyz.techrelay.playport.forever`, and its JIT helper
gets `xyz.techrelay.playport.forever.PlayportJIT`.

## Required inputs

This is **not** a turnkey build on a standard GitHub-hosted runner.
Playport's [build prerequisites](BUILDING.md) require an x86-64 Linux host with
LLVM **22.x** and Swift plus a rebuilt arm64ec LLVM-MinGW toolchain, Apple SDK
and additional native build tools. The workflow checks that these exist and
stops rather than manufacturing an invalid IPA.

Set these four GitHub Actions **repository secrets** under
Settings → Secrets and variables → Actions:

| Secret | Value |
| --- | --- |
| `PLAYPORT_SDK_ARCHIVE_URL` | Accessible HTTPS download URL for your own `tar.gz` of the extracted xtool Darwin SDK bundle |
| `PLAYPORT_SDK_SHA256` | SHA-256 of those exact `tar.gz` bytes |
| `PLAYPORT_MINGW_ARCHIVE_URL` | Accessible HTTPS download URL for the **already rebuilt** LLVM-MinGW 20260922 UCRT toolchain |
| `PLAYPORT_MINGW_SHA256` | SHA-256 of that exact `tar.gz` |

The SDK archive must extract without an extra top-level folder into the SDK
root configured as `DARWIN_SDK`; the MinGW archive must extract with `bin/`
and `aarch64-w64-mingw32/lib/libgcc.a` immediately under its root.
The archives must be lawfully obtained and hosted by you. No SDK or private
download token is committed to this public repository. The SHA-256 checks
prevent a changed archive from being used unnoticed.

GitHub's hosted Ubuntu image may not supply LLVM 22; the workflow explicitly
fails in the toolchain check when it doesn't. If it does, the build can still
exceed hosted runner disk or time limits (see [BUILDING.md](BUILDING.md#the-build-area)).
In that case use a prepared x86-64 Linux runner with sufficient disk, after
reviewing the workflow and adjusting its `runs-on` setting.

## Run

When the workflow file is on the default branch, open **Actions →
Playport Forever unsigned IPA → Run workflow** and select the branch
containing Forever. Download the `Playport-Forever-unsigned-IPA` artifact
from a successful run, unzip it and sign `Playport-Forever-unsigned.ipa`
with your on-device signing tool. The action does not install the app,
enable JIT or guarantee the Forever game itself is compatible.

The workflow is opt-in, read-only toward the repository, and keeps its
artifacts for seven days. A failing run is **not** a built IPA.
