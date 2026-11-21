# SDD ledger — plan: internal planning notes (not published)

- Request: validate the finished UART test and write code for sensors, RTC and GPIO.
- Ruling: inline execution in the existing project without worktree or initial commit, consistent with the context of a non-existent HEAD. Cost: no Git isolation; changes limited to new files and documentation.
- Design: SWD/Python/RAM on top of the existing primitives was chosen. UART DFU does not implement sensor commands. SPI requires traced pins. The already-requested work continues without an additional implementation-approval step.
- Task 1 complete: UART audit 349 attempts 344 ACK + 5 resync, valid transitions/TX/RX; RED module non-existent, GREEN 6 transport/RTC tests.
- Task 2 complete: RED orchestrator non-existent, GREEN 14 tests. Review extends the suite to 26 new tests; 47 total pass. C test passes.
- Final review: independent, read-only. 6 failures and 4 errors were reproduced in 10 regressions before fixing: RTC OFIE/SQW, time window with slow SWD, TX/metadata/sequence/empty audit, independent closure after hash failure, disconnected buffer level, full OD masks, no forced resume in baseline, MOSI before clock, incomplete transaction and adjacent I2C devices. GREEN 24 tests; additional failed-read boundary RED→GREEN, 26 new tests; suite 47/47.
- Failed-reset case: the test already passed when added because the earlier recovery covered it; it is not presented as RED→GREEN.
- Task 3 complete: real baseline, active suite of 24 pairs and closure checked. One pair SDA2/SCL17 incomplete; no new identification. This is not equivalent to an absent sensor. Subsequent UART ACK correct, hashes stable and P0.19 input. Physical SPI was not run for lack of traced pins.
- Final: the physical test is not considered out of scope: the results are in README/active-bounded and the limitations are explicit. The requested code and its verification are deliverable; physical identification of sensors is not claimed to have been achieved.
- No flash/UICR changes, no erase, no dependency installation, no processes left running.
