# Stage 6 — Automated Test, Diagnostics & Release Gate

## Narration (~140 words)

Every stage before this produced software. This stage decides whether it ships.

One command installs the framework with `uv`, starts two virtual ECUs — a FastAPI Battery Management System and a Body Domain Controller — and runs the full Robot Framework regression against them: battery monitoring, cell balancing, thermal management, and the HTTP integration suite. Thirty-eight real test cases, green in under ten seconds.

Then diagnostics. We drive a cell to 4.35 volts on the running BMS, the ECU raises an overvoltage fault, a CAN 0x102 fault frame goes out, and an ISO 14229 UDS session reads the stored DTC — P0A80 — clears it, and confirms the bus is clean.

Finally, Robot's `output.xml` is turned into a one-page release-gate scorecard: pass/fail per suite, duration, and a single PASS or BLOCKED verdict.

These are the same suites that later run against the real HIL rig — only the transport changes.

## What you're seeing

- `uv sync` + `vhil-start` bringing up the BMS (:8000) and BDC simulators as separate processes — test runner and ECUs decoupled like a real rig.
- Robot Framework `report.html` / `log.html` with green pass bars for all four functional suites (38/38).
- A terminal UDS session: `0x19` ReadDTC → inject fault → `P0A80` stored → `0x14` ClearDTC → `0x19` reads empty.
- `release_gate_scorecard.png` generated from `output.xml` — the artifact a release manager signs off on.
- Everything under `demo/out/` is produced by the run, not hand-made.

## Hand-off

Stage 6 closes the loop: the model from Stage 1 is now validated ECU software with an auditable, repeatable release gate — the same gate that runs nightly against physical HIL hardware.
