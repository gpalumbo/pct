# prototype2 Bug Report

**Branch:** `prototype2` (HEAD `9f9ffa5`)
**Date:** 2026-04-27
**Method:** Static analysis (`ruff`, `pyright`, `tsc`, `eslint`) + targeted manual review of high-risk modules.
**Scope:** Correctness bugs and type/lint issues. Security and performance reviews not in scope for this pass.

---

## Tooling summary

| Tool      | Where               | Status                                                 |
| --------- | ------------------- | ------------------------------------------------------ |
| ruff      | `backend/src`       | 39 findings (15 unsorted-imports, 7 line-too-long, 4 unused-imports, 3 raise-without-from, 3 suppressible-exception, 2 unused-vars, 2 lambda-assignment, 1 each: B023, SIM102, UP035) |
| pyright   | `backend/src/pct`   | 86 errors total. After excluding the cascading "module not found" noise from B-1 below, **42 real type/correctness errors remain**. |
| tsc       | `frontend`          | Clean once `npm install` was run. **0 errors.**        |
| eslint    | `frontend/src`      | 10 errors, 5 warnings.                                 |

Reproduce:

```
# backend
pip install -e backend
ruff check backend/src
pyright backend/src/pct

# frontend
cd frontend && npm install
npx tsc --noEmit
npx eslint src/
```

---

## Critical bugs (block runtime)

### B-1. Missing `pct.models` package — backend cannot import

29 source files import from `pct.models.{core,enums,agents,notifications,training,chat,workflow,imagegen}`, but **no `pct/models/` package exists** under `backend/src/pct/`. Every entry point that touches these modules fails with `ModuleNotFoundError: No module named 'pct.models'` at import time.

Verified:

```
$ python -c "import pct.main"
ModuleNotFoundError: No module named 'pct.models'
$ python -c "import pct.storage.task_io"
ModuleNotFoundError: No module named 'pct.models'
```

Affected files (all 29):

- `agent/__init__.py`, `agent/models.py`, `agent/model_downloader.py`, `agent/pool.py`, `agent/providers/local_llm.py`, `agent/tools/todo_tool.py`
- `board/models.py`, `board/pert.py`, `board/service.py`
- `chat/provider_factory.py`, `chat/router.py`
- `engine/auto_unblock.py`, `engine/execution.py`, `engine/scheduler.py`
- `imagegen/job_manager.py`, `imagegen/router.py`, `imagegen/service.py`
- `notifications/email.py`, `notifications/service.py`
- `settings/router.py`, `settings/service.py`, `settings/templates.py`
- `storage/chat_io.py`, `storage/feature_io.py`, `storage/project_io.py`, `storage/registry_io.py`, `storage/task_io.py`
- `training/models.py`, `training/service.py`

**Fix:** create the `pct/models/` package with `core.py`, `enums.py`, `agents.py`, `notifications.py`, `training.py`, `chat.py`, `workflow.py`, `imagegen.py` (or move the imports to wherever those classes are now defined — e.g. `pct/board/models.py` already defines `FeatureCreate`/`TaskCreate`, but no module defines `Project`, `Feature`, `Task`, `ErrorDetails`, `SmtpConfig`, `ProviderType`, `ExecutionStatus`, `FeatureStage`, `AgentType`, `TaskOutcome`, `ModelRegistryEntry`, `LoRARegistryEntry`, `WorkflowStage`, `ArtifactType`, `NotificationEvent`, `NotificationEventType`, `NotificationState`, `DownloadStatus`, `InclusionFlag`, `ResourceKind`, `ChatMessage`).

This single bug is the dominant source of pyright noise (44 of 86 errors) and must be fixed first.

---

## High-severity correctness bugs

### B-2. `imagegen/router.py:151` — `agent` possibly unbound after `try/except`

`backend/src/pct/imagegen/router.py:125-151`:

```python
try:
    project = load_project_config(settings.project_root)
    image_gen_agents = [a for a in project.agents if ...]   # NoneType risk too
    agent = None
    if req.model_id:
        agent = next((a for a in image_gen_agents if ...), None)
    if agent is None and image_gen_agents:
        agent = image_gen_agents[0]
    ...
except Exception:
    pass

resolved_agent_id = agent.id if agent is not None else None  # NameError if exception happened before line 131
```

If `load_project_config` raises (e.g. malformed config), the `except` swallows it but `agent` was never bound, so line 151 raises `UnboundLocalError`. Also `project.agents` on line 129 dereferences `None` if the config is missing — pyright flags this as `reportOptionalMemberAccess`.

**Fix:** initialize `agent = None` *before* the `try` block.

### B-3. `imagegen/router.py:417` — sort by an `object`-typed key

```python
items.sort(key=lambda x: x.get("created_at"))
```

`x.get("created_at")` returns `object`, which has no `__lt__`. At runtime this works only because every dict happens to have a string `created_at`; if any entry stores a different type (or `None`), the sort raises `TypeError`.

**Fix:** narrow the lambda return type, e.g. `key=lambda x: x.get("created_at") or ""`.

### B-4. `engine/scheduler.py` — schedules duplicate tasks; pool concurrency limit not applied

`backend/src/pct/engine/scheduler.py:34-55`:

1. `schedule_tasks` accepts an `AgentPool` argument and the docstring says "limited by the pool's semaphores" — but `pool` is **never read**. There is no concurrency cap; if 100 tasks are queued, 100 `asyncio.Task`s are spawned.
2. Race: `get_runnable_tasks` returns tasks in `queued` state. `execute_task` does not flip them to `running` until it actually runs (`execution.py:161`). If the scheduler is invoked again before the spawned task starts, the same `(feature_id, task_id)` is enqueued twice, producing duplicate attempts and corrupt `attempt-NNN` numbering.

**Fix:** acquire pool semaphore inside `execute_task` (or in scheduler before `create_task`); transition `queued → claimed` synchronously on save before yielding to the event loop.

### B-5. `engine/execution.py` — completed tasks never auto-unblock dependents

`execute_task` (`execution.py:135-241`) handles its own task lifecycle but never calls `engine.auto_unblock.check_unblocked` on success. Dependents stay blocked even after their dependency reaches the `done` stage. The auto_unblock module exists but is unreferenced by the engine.

```
$ grep -rn "check_unblocked\|auto_unblock" backend/src/pct/engine/
backend/src/pct/engine/auto_unblock.py:47:def check_unblocked(...)
# no callers
```

**Fix:** call `check_unblocked(project_root, feature_id, task_id)` after `task.execution_status = ExecutionStatus.idle` when the task lands on the done stage.

### B-6. `storage/feature_io.py:43-48` — `save_feature_spec` is non-atomic

```python
def save_feature_spec(project_root: Path, feature_id: str, content: str) -> None:
    admin_dir = _feature_admin_dir(project_root, feature_id)
    admin_dir.mkdir(parents=True, exist_ok=True)
    spec_path = admin_dir / "feature_spec.md"
    spec_path.write_text(content, encoding="utf-8")
```

Sister functions in the same file (`save_feature_metadata`) and across `storage/registry_io.py`, `storage/_atomic.py`, `storage/task_io.py` use `atomic_write`. This one path can be left half-written if the process crashes mid-write — surprising given the rest of the storage layer's invariant.

**Fix:** call `atomic_write(spec_path, content)` instead.

### B-7. `storage/chat_io.py:17-24` — concurrent SSE writes can interleave JSONL

```python
def append_message(project_root: Path, session_id: str, message: ChatMessage) -> None:
    ...
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
```

POSIX append is atomic only up to `PIPE_BUF` (typically 4 KiB). LLM tool-call messages can easily exceed that, so two concurrent appenders (e.g. multiple SSE chat streams or chat + imagegen on the same session) can produce a partial line and break `load_messages` on the next read.

**Fix:** serialize with an `asyncio.Lock` keyed by `session_id`, or use a fixed-size append buffer + flock, or chunk to ≤ `PIPE_BUF`.

### B-8. `storage/execution_io.py:_next_attempt_number` — race on concurrent attempts

```python
def write_attempt(...):
    attempt_num = _next_attempt_number(task_dir)
    attempt_dir = task_dir / f"attempt-{attempt_num:03d}"
    attempt_dir.mkdir()  # exist_ok=False → FileExistsError on race
```

Two coroutines for the same `task_id` (see B-4) compute the same `attempt_num` and the second `mkdir` raises. There's no try/retry.

**Fix:** loop with `mkdir(exist_ok=False)` and bump `attempt_num` on `FileExistsError`, or hold the per-task lock that B-4 should introduce.

### B-9. `frontend/src/api/sseStream.ts:24` — caller's external signal silently overrides controller

```ts
const controller = new AbortController();
const signal = externalSignal ?? controller.signal;
fetch(url, { ..., signal });
return controller;
```

When the caller passes `externalSignal`, the `controller` returned to them is **not wired to the fetch**. Calling `controller.abort()` on the returned controller does nothing; the stream runs until completion. The caller has no way to know which signal won.

**Fix:** chain signals — listen on `externalSignal` and call `controller.abort()`, or unconditionally use `controller.signal` and provide a way for the caller to forward an external abort.

### B-10. `git/merge.py:_run_git` returns code 0 on `None` returncode

`worktree.py`, `merge.py`, `post_merge.py`, `cleanup.py` all duplicate this helper and finish with `return proc.returncode or 0, ...`. If the subprocess somehow ends with `returncode=None` (process killed before reap, or shouldn't happen post-`communicate()`, but defensively still possible), the helper reports success. Unlikely to fire in practice but the comment "or 0" is misleading — at minimum it should be `proc.returncode if proc.returncode is not None else 1`.

Also: this helper is duplicated four times across the `git/` package. Extracting to `git/_subprocess.py` would prevent drift.

### B-11. `chat/context_builder.py:83,110` — calls non-existent `BoardService.read_artifact`

Pyright: `Cannot access attribute "read_artifact" for class "BoardService"`. Both call sites assume a method that doesn't exist on `BoardService`.

```
$ grep -rn "def read_artifact\|read_artifact" backend/src/pct/board/service.py
# no match
```

Any code path that hits these lines will raise `AttributeError`.

**Fix:** add `read_artifact(...)` to `BoardService`, or replace calls with the actual artifact-reading function (likely `storage.task_io.load_task_body` or similar).

### B-12. `chat/router.py:188` — calls non-existent `pct.board.service.get_task`

```python
task = service.get_task(...)
```

Pyright: `"get_task" is not a known attribute of module "pct.board.service"`. Same shape as B-11 — module-level attribute access of a function that was never defined.

### B-13. `chat/router.py:249` — passes raw `str` to a `Literal` role parameter

`ChatMessage(role=...)` expects `Literal['user','assistant','tool_result','imagegen_positive','imagegen_negative','imagegen_result']`, but the call site passes `str`. If the upstream value isn't one of those literals, pydantic raises a `ValidationError` and the chat turn fails.

**Fix:** validate/normalize the role at the boundary; reject early with a 400.

### B-14. `chat/router.py:208,223,347` — `feature_id`/`task_id`/`stage_id` may be `None`

Five call sites pass `str | None` into helpers typed `str`. If the request omits these fields, the helper either crashes or silently writes to a path containing the literal string `"None"` (because of `f"{value}"`).

**Fix:** validate request schema (use `Pydantic` `Required`) or guard each call.

### B-15. `agent/providers/local_llm.py:232,234,237,281,286` — sync/streaming response branches mishandled

`create_chat_completion` returns either a single `ChatCompletion` or an `Iterator[CreateChatCompletionStreamResponse]` depending on `stream=True/False`. The code does:

```python
resp = llm.create_chat_completion(messages=msgs, stream=...)
return resp["choices"][0]["message"]["content"]
```

Pyright catches that you can't subscript an `Iterator`. Concretely:

- Line 234: indexing an iterator instead of consuming it.
- Line 286: subscripting a `str`.

These look like the streaming branch was never tested end-to-end; non-streaming may work by luck but the streaming branch will raise `TypeError`.

### B-16. `board/dag_validation.py:49-51` — `parse_wikilink` may return `None` keys

`parse_wikilink` returns `tuple[str | None, str | None]`. The DAG builder unpacks and uses both halves as dict keys / list elements without a `None` check. A malformed wikilink (e.g. `[[]]` or `[[#task]]`) silently inserts `None` keys into the graph.

### B-17. `agent/chat_loop.py:10` — imports `TaskOutcome` from `pct.agent.models` which doesn't define it locally

The import succeeds today only because `agent/models.py` re-exports from the missing `pct.models.enums` (B-1). Pyright flags `"TaskOutcome" is unknown import symbol`. Once B-1 is fixed in a way that drops the re-export, this import breaks.

### B-18. `agent/chat_loop.py:136-154` — `result` possibly unbound on first-iteration timeout

In `execute_chat_turn`, the `for...else` writes `result.error = "..."` but if `range(max_tool_iterations + 1)` is empty (caller passes `max_tool_iterations < 0`) or if an exception fires inside the very first `provider.execute(...)` (caught at line 141 where the function returns), then `result` is unbound at the `else`. The control flow is also brittle: the `except TimeoutError: raise` does not assign `result`, so if the next exception path is `Exception` instead, `result` stays unbound. Pyright flags 5 sites at lines 136, 137, 151, 152, 154.

**Fix:** initialize `result = AgentResult(outcome=TaskOutcome.error, error="empty")` before the loop, or restructure the `else` clause.

### B-19. `imagegen/service.py:430` — `Object of type 'None' cannot be called`

Pyright: pipeline callable is checked elsewhere but used here without a guard. If the pipeline failed to load and returned `None`, this site `raises TypeError: 'NoneType' object is not callable`.

### B-20. `imagegen/service.py:393, 432, 435` — int/float seed mismatch

`torch.manual_seed` takes `int`; we pass `int | float` (and store it on a list typed `tuple[Any, int]`). With a fractional seed this would have raised at runtime, but more commonly the value is fine — still a real type narrowing bug worth fixing because seeds end up persisted to chat history.

### B-21. `chat/provider_factory.py:70` — return type narrowed too aggressively

`resolve_provider` returns `tuple[ClaudeCodeProvider, AgentConfig]` from one branch and the protocol expects `tuple[AgentProvider, AgentConfig]`. Concrete-to-protocol assignment fails because pyright wants the function annotated with the wider type.

### B-22. `settings/router.py:137,149` — `RepoFolder.rfilename` does not exist

The huggingface_hub `RepoFolder` class has no `rfilename` attribute; only `RepoFile` does. The code mixes them in one iteration:

```python
for entry in repo_tree:
    if entry.rfilename.endswith(".gguf"):  # AttributeError on folders
```

**Fix:** branch on `isinstance(entry, RepoFile)` first.

---

## Medium-severity bugs

### M-1. ruff B904 — exception chaining lost in `settings/router.py`

3 sites raise `HTTPException` from inside `except` blocks without `raise ... from err`. The original traceback is lost, making errors hard to diagnose.

`settings/router.py:126`, `settings/router.py:141`, `settings/templates.py` (via tool config).

### M-2. ruff B023 — function captures loop variable (closure bug)

One site closes over a loop variable that mutates each iteration; the closures all see the final value. Common cause of off-by-one bugs in async fan-out.

(Run `ruff check backend/src --select=B023 --output-format=concise` for the exact location.)

### M-3. ruff F841 — assigned-but-unused variables (×2)

Likely indicates intent that was never wired — e.g. a result computed and discarded.

### M-4. ruff F401 — unused imports (×4)

Confusing maintenance signal; remove or wire them up.

### M-5. ruff E731 — lambda assigned to a name (×2)

Style nit per ruff but in practice obscures the function name in tracebacks.

### M-6. ruff SIM105 — `try/except/pass` instead of `contextlib.suppress` (×3)

Functional but verbose; more importantly, `pass`-on-bare-`except` patterns hide real bugs (notably the ones in B-2 and `imagegen/router.py:146`).

### M-7. eslint `no-explicit-any` errors in `TaskDetailPanel.tsx` (×4 lines: 225, 243, 279, 297)

Loses type safety in the highest-traffic component.

### M-8. eslint react-hooks/exhaustive-deps warnings (×5)

Each is a stale-closure foot-gun. Highest-impact ones:

- `ArtifactOutputPane.tsx:197` — missing `imageGenAgents` dep (Effect runs once with first agent list)
- `ArtifactOutputPane.tsx:208` — missing `imageGenAgent` dep
- `Swimlane.tsx:21` — missing `feature` dep (memoized title may go stale)
- `KanbanBoard.tsx:23` — `stages` falsy-fallback inside useMemo deps
- `WorkflowTab.tsx:49` — same shape as KanbanBoard

### M-9. eslint `no-unused-vars` errors using underscore-prefix convention

5 errors in `configApi.ts`, `ArtifactEditorModal.tsx`, `ImageGalleryModal.tsx`, `ImageGenPane.tsx`. The `_taskId`/`_featureId` props are accepted but never read — likely dead parameters from refactors.

### M-10. `imagegen/router.py:131` — `try/except: pass` swallows config errors

Even after B-2 is fixed, the bare `except Exception: pass` masks any real failure (permissions, malformed YAML). Log at `warning` and continue with defaults.

### M-11. ruff E501 — 7 long lines

Code style only.

### M-12. ruff I001 / UP035 — 15 unsorted import blocks, 1 deprecated typing import

`ruff check --fix` resolves all 15+8 of these mechanically.

---

## Low-severity / style

- `backend/pyproject.toml` does not configure pyright; running `pyright` from any cwd works because the helper finds `pyrightconfig.json` (none exists). Add `[tool.pyright]` with `include = ["src"]` and `pythonVersion = "3.11"` to make CI deterministic.
- `frontend/package.json` declares ESLint v8 deps but the global ESLint is v10 — `npx eslint` works because `npm install` provides the local v8. Document this.
- `git/_run_git` is duplicated in 4 files. Extract.
- `frontend/src/api/sseStream.ts:67` — silently `// skip malformed lines` hides decode bugs. Log to console in dev.

---

## Verification

After each fix:

1. `ruff check backend/src` should drop monotonically toward 0.
2. `pyright backend/src/pct` should drop from 86 → near 0 (most go away once B-1 is resolved).
3. `python -c "import pct.main"` must succeed (currently raises `ModuleNotFoundError`).
4. `cd frontend && npx tsc --noEmit` must remain at 0 errors.
5. `cd frontend && npx eslint src/` should reach 0 errors / 0 warnings.
6. End-to-end smoke: start backend (`uvicorn pct.main:app`), open frontend (`npm run dev`), create a project, queue a task, watch it auto-unblock its dependents, confirm execution attempts numbered correctly under load.

---

## Suggested fix ordering

1. **B-1** (missing `pct.models`) — unblocks everything else and removes ~half the pyright noise.
2. **B-11, B-12, B-17** — symbol-resolution bugs that probably go away or sharpen once B-1 lands.
3. **B-2, B-18, B-19** — possibly-unbound runtime crashes.
4. **B-4, B-5, B-7, B-8** — concurrency / lifecycle bugs that corrupt state under load.
5. **B-6, B-9, B-13, B-14, B-15, B-22** — focused fixes per call site.
6. **B-10, B-16, B-20, B-21, B-3** — narrower correctness issues.
7. M-series and ruff/eslint sweep last (`ruff check --fix backend/src` does most of the heavy lifting).
