# SDD ledger — plan: monitor DFU UART, 2026 (internal planning notes, not published)

- Plan without a separate spec; the plan is the contract.
- Pre-flight: tasks 1→2 share the decoder/validator; 2→3 the CLI and JSONL record. No conflict.
- Ruling: work in the existing project without a worktree or commits — the plan asks for this explicitly and HEAD does not exist yet; creating a commit of the whole project would exceed this change — cost: no Git isolation, preserve unrelated changes.
- Baseline: 7 Python tests pass. Pico Debugprobe E660C0D1C75C942F present; /dev/cu.usbmodem21102. The port was not opened and nothing was transmitted.
- Hardware: r26 removed E1/E2 and connected E/SWO→GP5; last documented power supply 6 V H/F, C/F~2 V. Physical r15 confirmation pending.
- Task 1: complete — RED: 6 failures, including an accepted echo; GREEN: 5 CLI/PTY tests, 0 failures (`green-task1.txt`).
- Task 2: complete — RED: 6 tests fail because of missing options; GREEN: 12 CLI/PTY tests, 0 failures (`green-task2.txt`).
- Commit-based ledger tools do not apply to a nonexistent HEAD: this ledger and the evidence are kept in the project per the plan, without an initial commit of unrelated files.
- Independent final review in progress; the setup has not been changed and the real UART has not been opened.
- Final review: an independent reviewer read the code/plan/sources and ran the 12 tests. Two important issues, both confirmed in `red-review.txt` and fixed in `green-review.txt`: reject B0 before opening; close the sample after processing a block with an ACK so that success is preserved if a disconnection follows. Full suite: 21/21.
- Minor review cleanup: duplicate import removed and unittest.main moved to the bottom (no change in monitor behavior).
- Final: physical validation is not considered out of scope: it remains pending for lack of r15 confirmation; software delivery leaves that physical action pending. No success on the unit is claimed.
- Integration: keep in the existing project without commit/merge/PR, in line with the plan and the nonexistent HEAD. There is no temporary workspace to remove.

- Task 3: complete — r15 setup confirmed by the owner; port 21202, valid ping and 20/20 ACK; frames, sequences and summary cross-checked. Physical evidence in unit-20261119T113146-0500. Run closed; no monitor in the background.
