Thanks for the correction. "The model is never asked" was wrong, and I have fixed it in our notes. Below is what I re-checked through the SDK, then a proposal.

## Re-check on current `dev` (`aa7d5b6b`)

Actual `Agent.run(message, tools=[])` with a controlled provider: every provider call gets a canned text reply `PONG`, and the network is disabled. Automatic fact extraction is off in this config. No paid request was made.

| Input | Provider calls (whole turn) | `body` | `run_state` | Response metadata |
| --- | --- | --- | --- | --- |
| 12,000 chars | 3 | `docdrift: PONG` | `completed` | `brain_status=done`, `respond_kind=assistant` |
| 12,001 chars | 3 | `docdrift: I could not safely update the task conditions. …` | `completed` | `brain_status=waiting_user`, `brain_working_status=waiting_user`, `respond_kind=assistant`, `finish_reason=stop` |

In the 12,001 case the strings `invalid_task_context_update`, `invalid_or_missing_update` and `clarify` do not appear anywhere in the returned result (`raw`, metadata or stats), and there is no `clarify_request` or `clarify_id`. So the provider is called on both sides of the bound, as you found, and the only structured difference the SDK receives today is `brain_status=waiting_user`.

## What I read in source (same head)

- `resolve_entry_task_update` (`modules/brain/loop/context/task_context.py:158`): with no active task and no patch, it seeds `ResolvedTaskContext(objective=str(user_input), objective_kind="verbatim")` (line 191). Above 12,000 characters that model validation raises, and the error is a `ValueError`.
- `apply_entry_task_context` (`modules/brain/loop/context/task_entry.py:142`) handles every `ValueError` the same way: event `brain.task_context.rejected` with reason `invalid_or_missing_update`, and a decision with `reason_code="invalid_task_context_update"`, `respond_kind="clarify"` and the fixed restate question. After this point a revision mismatch, a wrong quote, a missing update for an active task (#719) and this capacity rejection are indistinguishable.
- Response metadata: `respond_kind` is `step_out.kind or "assistant"` (`services/brain/post_execution/postprocess_response.py:143`). `clarify_request` is attached only when `unresolved_clarify_items` is non-empty (`postprocess_clarify.py`), which it is not here.
- SDK: `Agent._run_once` coerces `raw["body"]` (`api/agent.py:370`) without consulting metadata. With `output_type`, the restate question becomes an output-validation failure.

## Proposed bounded correction

Three small parts, each in its existing owner. I am happy to be redirected on any of them.

1. **Task-context failure owner.** Give the verbatim-seed capacity rejection its own reason instead of folding it into `invalid_task_context_update`. Detect it where the seed is built, and return a decision with a distinct `reason_code` (for example `task_context_capacity_exceeded`) and a question that states what happened: the request is longer than the task context can hold, so shorten or split it. The 12,000 bound is unchanged, nothing is truncated, and model-supplied updates keep their current validation and reason.
2. **Response owner.** Carry the reason of a task-context clarify decision to the API response as a structured fact. Either (a) populate the existing `clarify_request` metadata for these structural clarifies, since it already has `questions[].reason_code`, or (b) add one metadata fact for the decision reason next to `brain_status`. No new `run_state`.
3. **SDK, before output coercion.** This looks like the same contract you described in #770 and #852: the structured outcome is in the response, and output coercion then hides it. I do not want to open a competing change. If one shared outcome-before-coercion step is planned there, #804 only needs parts 1 and 2 to feed it a reason. If #804 should carry its own minimal check instead, it would be: when the response carries the task-context reason from part 2, `Agent._run_once` does not coerce the question as model output, and with `output_type` set it raises the existing `AgentOutputValidationError` naming that reason, with `raw_text` unchanged. It would key on the structured reason, not on `waiting_user` alone and not on prose.

## Neighbor controls I would add (controlled provider, actual `Agent.run`)

- new task at 12,000 characters: answer returned and task context created, unchanged;
- new task at 12,001 characters: capacity reason in metadata, truthful question, no task context, no truncation;
- existing task with a valid `update`: unchanged;
- existing task with a missing or invalid update: still `invalid_task_context_update`, so #719 stays separate;
- genuine model clarification: still a clarify, with its current metadata unchanged;
- cancellation: the `entry_task_cancelled` answer is unchanged.

## Two questions before I write anything

1. For part 2, is (a) or (b) the right owner?
2. For part 3, should #804 wait for the shared outcome-before-coercion work in #770 and #852, or carry its own minimal check?

If the direction is acceptable, I can open a PR against `dev` with part 1 alone first, since it is the smallest and independently testable, then part 2. Part 3 would follow your answer to question 2.
