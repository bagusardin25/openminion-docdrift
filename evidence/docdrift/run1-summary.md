# Run 1 (baseline) — summary

The full `report.json` for this run was overwritten by run 2. This summary is
transcribed from the run's console log and the report printout taken right
after the run.

- openminion 0.1.23 vs `openminion-v0.1.23 @ 695ba66`, `gpt-4.1-mini`, `--issues no`
- 165 snippets, 5 candidates

## Console log

```
[2/5] triage
      D3cdd8d1: real_drift      (docs/guides/blockchain-tools.md, 26 vars)
      Dde1f158: out_of_scope    (docs/runtime-database-upgrades.md, 1 var)
      Debb6ed1: real_drift      (docs/security-scanning.md, 13 vars)
      D2472d8f: real_drift      (docs/system-operations.md, 6 vars)
      D22f9339: real_drift      (docs/testing-and-validation.md, 5 vars)
[3/5] claims
      docs/turn-budgets.md:8-30            supported 5
      docs/provider-capabilities.md:72-88  supported 3, unverifiable 1
      docs/task-context.md:40-63           unverifiable 5
      docs/runtime-surfaces.md:34-125      supported 5
[4/5] review: D3cdd8d1, Debb6ed1, D2472d8f, D22f9339 -> all "confirmed"
[5/5] issues: 4 issue turns; 3 approval prompts shown and denied (--issues no);
      the Debb6ed1 turn ended without calling write_issue_draft
report: 4 confirmed, 0 disputed, 0 failed turn(s)
```

## Turn timings (seconds / tool calls)

| Role | Item | s | tools |
| --- | --- | --- | --- |
| triage | blockchain-tools | 32.1 | 1 |
| triage | runtime-database-upgrades | 79.6 | 2 |
| triage | security-scanning | 14.4 | 2 |
| triage | system-operations | 17.5 | 2 |
| triage | testing-and-validation | 17.1 | 1 |
| claims | turn-budgets | 31.4 | 5 |
| claims | provider-capabilities | 32.9 | 4 |
| claims | task-context | 27.2 | 5 |
| claims | runtime-surfaces | 29.5 | 3 |
| reviewer | ×4 | 15.2 / 13.6 / 14.5 / 16.4 | 2 / 2 / 6 / 5 |
| issue | ×4 | 7.8 / 14.7 / 8.1 / 6.9 | 0 (denied) |

## Manual verification afterwards

`git grep` in the checkout showed every flagged variable is used under `tests/`
or `.github/`, or built from
`APPROVAL_PREFIX = "OPENMINION_BLOCKCHAIN_TESTNET_WRITE_APPROVED_"`
(`tests/e2e/runners/run_blockchain_testnet_write.py:38`). All 4 "confirmed"
findings were false positives.
