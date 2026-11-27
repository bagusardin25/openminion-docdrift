Refs #804 (part 1 only).

- A new request over the 12,000-character task-context bound, sent without a model-supplied `task_update`, is seeded verbatim as the task objective. That seed fails `ResolvedTaskContext` validation, and `apply_entry_task_context` folds the failure into `invalid_task_context_update` with the generic "I could not safely update the task conditions" question: the same reason as a revision mismatch, a wrong quote or #719.
- The seed owner, `resolve_entry_task_update`, now raises `TaskContextCapacityError` (a `ValueError`, beside the existing `TaskContextBudgetError`) when that verbatim seed fails. The existing failure owner, `apply_entry_task_context`, returns a clarify decision with `reason_code="task_context_capacity_exceeded"`, emits `brain.task_context.rejected` with that reason, and asks a question that states the request's length and the task-context limit for a verbatim seed, not a general message-size limit.
- Unchanged: the 12,000 bound and `ResolvedTaskContext` validation, the oversized-first-input instruction from f2931245, no truncation, the task state a rejection leaves (`resolved_task_context` stays empty and `task_context_needs_update` is set), and every other task-update failure, which still returns `invalid_task_context_update`.
- Held, as asked on #804: carrying the reason to response metadata (part 2) and outcome handling before SDK output coercion (part 3, with #770/#852). An SDK caller now receives the truthful question as the reply text; the reason code is not yet in `AgentRunResult` metadata.

Self-review evidence

- Reviewed head and base: `385bba62` on `fix/804-task-context-capacity-reason`, base `dev` at `99f3e657`. This is `029c34b0` rebased onto current `dev` to resolve a `CHANGELOG.md` conflict with the new security-repair entry: both Unreleased entries are kept unchanged. The source and test diff is identical to `029c34b0` (`git patch-id --stable` `c08f7f06afa6` for both), and so are the added changelog lines.
- Changed files: `modules/brain/loop/context/task_context.py` (verbatim-seed construction), `modules/brain/loop/context/task_entry.py` (task-context failure owner), two existing test files, and `CHANGELOG.md` (Unreleased). `resolve_entry_task_update` has one caller, `apply_entry_task_context`, which has one caller in `loop/orchestration.py`. The `TaskContextBudgetError` handler in `orchestration.py` covers provider calls only and is untouched.
- Simplicity: no new mode, fallback or retry. One exception class beside `TaskContextBudgetError` and one `except` clause in the existing owner. The only comment says why a `ValidationError` there can only be the capacity bound: the objective is the seed's only variable field, and empty input returns earlier.
- Regression control: with the source change reverted and the new tests kept, exactly the two capacity cases fail, still getting `invalid_task_context_update`: `test_initial_verbatim_capacity_failure_has_its_own_reason[12001-False-task_context_capacity_exceeded]` and `test_first_input_requests_compact_model_task_without_truncation[True-False]`. The four neighbouring cases in those tests pass before and after.
- Neighbour controls, unchanged and passing:
  - exact boundary: a 12,000-character first input is still seeded verbatim;
  - existing task with an oversized message and no update: still `invalid_task_context_update`, event reason `invalid_or_missing_update`;
  - valid model `start` update for an oversized first input: resolved objective, no rejection;
  - malformed and external-task updates: `test_malformed_model_sidecar_is_rejected_as_a_decision_not_an_exception`, `test_pending_external_job_prevents_context_change_without_owner`;
  - genuine clarification: `test_unified_entry_clarify_path_returns_waiting_question`;
  - cancellation: `test_cancel_clears_task_and_cannot_fall_back_to_old_goal`, `test_cancel_cannot_be_combined_with_tool_execution`, `test_context_cancellation_cannot_falsely_cancel_an_external_task`.

Validation

Local: Windows 11, Python 3.11.9, `uv sync --extra dev --python 3.11`.

On `385bba62` (base `99f3e657`), after the rebase:

- the pytest command below: 218 passed;
- `python -m ruff check .`: all checks passed; `python -m ruff format --check` on the four changed Python files: already formatted.

On `029c34b0` (base `4bdc03a5`), before the rebase:

- `python -m pytest -q tests/brain/test_resolved_task_context.py tests/brain/test_task_context_affordable_requests.py tests/brain/test_unified_turn_entry.py tests/brain/test_runner_decision.py tests/api/test_agent.py`: 218 passed.
- `python -m ruff check .`: all checks passed. `python -m ruff format --check` on the four changed Python files: already formatted.
- `python -m mypy src/openminion/modules/brain/loop/context/task_context.py src/openminion/modules/brain/loop/context/task_entry.py --follow-imports=silent --ignore-missing-imports`: 2 errors, both also present on `dev` at `4bdc03a5` (the `RespondDecision` re-export at line 6 and the return type in `build_task_entry_context`). None is on a changed line.
- Actual `Agent.run(message, tools=[])` through the SDK with a controlled provider (every provider call answers `PONG`, network disabled, no paid request), before and after on the same base:

| Input | `dev` at `4bdc03a5` | this branch |
| --- | --- | --- |
| 12,000 chars | `PONG`; `brain_status=done`; 3 provider calls | unchanged |
| 12,001 chars | "I could not safely update the task conditions. Please restate the current task and its required conditions."; `brain_status=waiting_user`; 3 provider calls | "This request is too long to start as a task: it has 12,001 characters, and the task context holds a new request word for word only up to 12,000. Please shorten it or split it into smaller requests."; `brain_status=waiting_user`; 3 provider calls |

Not run locally: `make lint` and `make ci-check` (no `make` in this Windows environment); hosted CI covers them. `scripts/validate/test_skip_budget.py` reports a mismatch on this machine between Windows `\` paths and the baseline's `/` paths, for files this PR does not touch; this PR adds no skip or xfail markers. The first local run of the two changed test files hit the 60 s pytest timeout once, inside a shell lookup (`shutil.which` in `tools/exec/process.py`) on a cold environment; every later run passed.

Contributor review

- [x] I completed the [required self-review](https://github.com/openminion/openminion/blob/dev/CODE_QUALITY.md#required-self-review-before-submission) on the full final diff and each new delta, including comments/docstrings in source, tests and scripts.
- [x] I used the smallest clear change in the existing owner, justified new structure or defenses against actual callers/failures, and preserved affected behavior and boundary contracts.
- [x] My controls exercise the affected path; I did not weaken assertions, add skips/xfails, retry failures or raise quality ceilings to obtain a green result.
- [x] I updated affected public guidance and release notes, kept unrelated cleanup out, and labelled historical evidence accurately.
- [x] For a broad cleanup claim, I linked the live inventory, per-file dispositions and remaining work; otherwise I explained why it does not apply. Not applicable: this is a bounded fix, not a cleanup.