# Audit — 2026-10-23

Scope: CLI checks, diagnostic output, report storage, per-user installer,
GitHub workflows and Arch packaging. Baseline: `1446f40`.

| Finding | Impact | Resolution in 0.2.0 |
| --- | --- | --- |
| Missing `paccheck` can be reported as missing package files | Medium | Separate tool execution failures before classifying file diagnostics |
| Restricted crash journals can appear healthy when no dumps are visible | Medium | Treat limited access as NOT CHECKED |
| Malformed or incomplete JSON aborts the report | Medium | Validate root and nested values, continue with remaining checks |
| SMART failure bit is only a warning; partial access can be hidden by warning counters | Medium | Apply smartctl bitmask precedence; use a separate sentinel outside the eight-bit mask for execution failures |
| NaN, strings and invalid sensor values can crash or appear healthy | Medium | Validate finite numeric values and critical thresholds |
| Diagnostic control sequences can affect terminal state and persist in saved reports | Medium | Sanitize all displayed and saved diagnostic text, including truncated tails |
| Report directory may retain loose permissions or follow a final symlink | Low | Check ownership, reject a symlink, use descriptor-relative exclusive creation, directory 0700 and files 0600 |
| Installer follows existing destination symlinks | Low | Atomically replace the destination entries |
| Missing sudo, terminal spawn errors or report-write errors can raise tracebacks | Low | Continue available checks, try the next terminal, and report storage failures with exit status 1 |
| CI only tests unsupported Python 3.9 | Low | Test Python 3.11, 3.14 and 3.15; refresh pinned Actions and add Dependabot |

Validation: 31 regression tests pass on local Python 3.14, including simulated
SMART flags and malformed tool output. CLI help/version, Python compilation,
workflow actionlint, desktop-file validation and whitespace checks pass.
Arch package 0.2.0-1 was built locally with makepkg using the published source
commit. All three source checksums passed; generated .SRCINFO matches PKGBUILD.
The package was built without installing it or its dependencies.

Tests use temporary directories and a local bare Git remote. No actual AUR
publication, sudo authentication, disk self-test, installed-package update or
system configuration change is performed. Live hardware health is outside
this source audit; SMART behavior is tested with fixtures.

## Compact output — version 0.3.0

The default terminal output is a single grouped overview. Historical events
are separate from current findings. The full private report retains all
sanitized diagnostic lines; `--verbose` displays diagnostic detail in the
terminal. Unavailable checks remain visible, and disk health errors retain
the ERROR status and a backup recommendation.

Validation: 40 regression tests, including a report with 80 stack-trace lines,
14 temperature sensors, partial coverage, restricted SMART access and actual
SMART failure flags. The representative compact output fits within 24 lines
at a 100-column terminal width. The detailed file retains the complete input.
