# PCT — Technical Specification v0.1 (Draft)

---

## 1. Storage Architecture

### Overview

All PCT project state lives under `$PCT_PROJECT_ROOT`. Within the project root, items are split into two categories:

1. **`pct-admin/`** (checked into git) — specs, task definitions, project-level configuration that humans and AI both read/write
2. **`.pct/`** (git-ignored) — execution artifacts, RAG index, chat transcripts, kanban snapshots — large or machine-generated data

Outside the project, only cross-project reusable data lives at a global location:

3. **`~/.pct/`** — curation data (prompt templates, training examples, LoRAs), registries, user config

### Design Principles

- **All project state is local.** Everything PCT needs for a project lives under `$PCT_PROJECT_ROOT`. No symlinks, no `~/.pct/projects/` indirection. The project directory is self-contained.
- **Checked-in vs. ignored is an explicit boundary.** `pct-admin/` is committed — specs, tasks, and metadata travel with the repo. `.pct/` is ignored — execution artifacts, embeddings, and transcripts stay local.
- **Specs are authoritative.** The AI reads and writes specs and task definitions in `pct-admin/`. These are small, human-readable, and useful to keep with the project.
- **No duplication.** Each piece of data has exactly one home. Specs and status live in `pct-admin/`. Execution details live in `.pct/`. They reference each other by task ID.
- **PCT is the orchestrator.** AI agents don't need to know the directory structure. PCT assembles paths and context for each invocation. RAG is the primary interface agents use to query project data — specs, task history, and execution artifacts are indexed and retrieved through vector search rather than direct file access.

### Directory Structure

#### Project Root: `$PCT_PROJECT_ROOT`

```
$PCT_PROJECT_ROOT/
  pct.yaml                              # project config (checked in)

  pct-admin/                            # ── CHECKED INTO GIT ──
    project_spec.md                     # project-level specification
    active-features/
      f1-core-server/
        feature_spec.md                 # feature-level specification
        metadata.yaml                   # lifecycle stage, dependencies,
                                        #   worktree path, branch
        tasks/
          define-data-models.md         # task definition + current status
          design-api-routes.md
          setup-scaffold.md
      f2-frontend-kanban/
        feature_spec.md
        metadata.yaml
        tasks/
          design-component-tree.md
    feature_backlog/
      agent-execution-engine.md         # feature specs not yet activated
      git-integration.md                #   (no tasks/ dir until activated)

  .pct/                                 # ── GIT-IGNORED ──
    execution/
      active-tasks/                     # tasks currently in progress
        define-data-models/
          attempt-001/
            agent_log.jsonl             # raw LLM messages
            output.md                   # agent's produced output
            feedback.md                 # rejection feedback (if rejected)
            metadata.yaml               # timestamp, agent, model, duration, tokens
          attempt-002/
            ...
      completed-tasks/                  # archived after task reaches done
        design-component-tree/
          attempt-001/
            ...
      features/                         # feature-level execution artifacts
        f1-core-server/
          integration-test/
            attempt-001/
              agent_log.jsonl
              output.md
              metadata.yaml
    chat_history/
      planning-001.jsonl                # planning session transcripts
      planning-002.jsonl
    rag/
      tasks.lance/                      # LanceDB table: task execution embeddings
      specs.lance/                      # LanceDB table: spec/feature embeddings
    kanban_snapshots/                    # periodic board state captures

  work/                                 # ── TASK OUTPUT ARTIFACTS ──
    INDEX.md                            # auto-generated index
    f1-core-server/
      define-data-models/
        ...
```

#### `pct.yaml` (project root, checked in)

Project configuration: project ID, workflow stages, agent defaults, concurrency limits, notification settings. See Object Model §4.1 (Project) for the full schema.

```yaml
id: "myapp"
name: "My Application"
project_type: "code"
directory: "C:/Users/gordo/projects/myapp"
default_agent_id: "claude-code"
planning_agent_id: "claude-code"
context_manager_agent_id: "haiku-summarizer"
context_manager_prompt: "Summarize the following context..."
max_remote_agents: 2
max_local_agents: 1
notification_email: null
font_size: 14
workflow_stages:
  - id: "refine-spec"
    label: "Refine Spec"
    enabled: true
    agent_id: null
    prompt_template: ""
    auto_run: false
    sort_order: 1
  - id: "implement"
    label: "Implement"
    enabled: true
    agent_id: "claude-code"
    prompt_template: "Implement the following task..."
    auto_run: true
    sort_order: 2
  # ... additional stages
template_variables:
  - key: "style_guide"
    description: "Project style conventions"
    value: "Use concise prose, active voice..."
artifact_types:
  - id: "chapter"
    label: "Chapter"
    template_hint: "Write narrative prose with dialogue and pacing..."
  - id: "character"
    label: "Character"
    template_hint: "Create a character profile with backstory..."
  # ... additional artifact types
```

#### `pct-admin/` — checked into git

**What lives here:**
- `project_spec.md` — top-level project specification
- `active-features/{feature_id}/feature_spec.md` — feature-level specifications
- `active-features/{feature_id}/metadata.yaml` — feature lifecycle stage, cross-feature dependencies, swimlane state, worktree path, branch name
- `active-features/{feature_id}/tasks/{task_id}.md` — task definitions including current workflow stage, execution status, dependencies (`blocked_by`, `cross_refs`), artifact type
- `feature_backlog/` — feature specs for features not yet started (no `metadata.yaml` or `tasks/` dir until activated)

Feature lifecycle state is encoded at two levels: the directory location (`active-features/` vs `feature_backlog/`) and the `metadata.yaml` lifecycle stage field (Planning, Active, Suspended, Integration Test, Complete).

**What does NOT live here:** agent execution logs, attempt outputs, RAG embeddings, chat transcripts — anything large or machine-generated.

**Size expectation:** A few KB per task, a few hundred KB total for a large project. Negligible git impact.

#### `.pct/` — git-ignored

**What lives here:**
- `execution/active-tasks/` — execution artifacts for in-progress tasks, each with attempt subdirectories
- `execution/completed-tasks/` — archived execution artifacts for finished tasks (moved from `active-tasks/` when task reaches done)
- `execution/features/` — feature-level execution artifacts, primarily integration test attempts
- `chat_history/` — planning session transcripts (JSONL of messages)
- `rag/` — LanceDB tables (Lance columnar files) for vector search over task history and specs
- `kanban_snapshots/` — periodic captures of the full board state (for history/timeline features)

**Size expectation:** Can grow to many MB over the life of a project. Never committed.

#### Task File Format

The full field specification for tasks is defined in the Object Model (§4.4, Task). The frontmatter is YAML; the body is human-readable Markdown. The AI reads and writes both. Attempt details are brief references — full outputs live in `.pct/execution/`.

**Example task file:**

```markdown
---
id: "define-data-models"
title: "Define data models"
feature_id: "f1-core-server"
current_stage_id: "code-review"
artifact_type_id: "text"
blocked_by:
  - "[[f1-core-server#setup-scaffold]]"
cross_refs:
  - "[[f2-frontend-kanban#design-component-tree]]"
execution_status: "idle"
is_bypassed: false
consistency_flag: null
created_at: "2026-02-12T10:00:00Z"
updated_at: "2026-02-12T14:30:00Z"
---

# Define Data Models

## Spec
Define Pydantic models for Project, Feature, Task, Agent, and WorkflowStage.
Models should be persisted to JSON files. Do not use SQLAlchemy or any ORM.

## Acceptance Criteria
- All core models defined with full field specifications
- JSON serialization/deserialization methods
- Validation rules for required fields

## Notes
- Attempt 1 rejected: used SQLAlchemy (see execution log for details)
- Attempt 2 rejected at code review: missing status_history field
- Attempt 3 in progress
```

#### Global: `~/.pct/`

```
~/.pct/
  curation/
    prompt_templates/
      v1/
        refine-spec.md
        implement-code.md
        implement-content.md
        code-review.md
        refactor-check.md
      v2/
        ...
    training_data/
      positive/
      negative/
    loras/
      code-style-v1/
    agent_configs/
      claude-code.yaml
      local-llama.yaml
  registries/
    models.yaml                       # model registry entries
    loras.yaml                        # LoRA adapter registry
  users/
    users.json                        # user authentication data
```

**What lives here:**
- Versioned prompt templates (reusable across projects)
- Curated training examples (positive and negative, from any project)
- Trained LoRA weights
- Agent configuration presets
- Model and LoRA registries (cross-project)
- User authentication data

### How AI Agents Interact with Storage

| Session Type | AI reads from | AI writes to |
|-------------|---------------|--------------|
| **Planning** | `pct-admin/` (specs, existing tasks) | `pct-admin/` (new/updated specs and task files) |
| **Implementation** | `pct-admin/` (task spec) + worktree (existing code) | Worktree (new code) |
| **Code Review** | `pct-admin/` (task spec) + worktree (diff/changes) | `pct-admin/` (review notes appended to task file) |
| **Refactoring Check** | `pct-admin/` (project spec) + project repo (merged code) | `pct-admin/` (new task files if opportunities found) |

PCT handles writing to `.pct/execution/` — the AI doesn't touch it directly. PCT captures the agent's output stream and stores it after execution completes.

---

## 2. Tech Stack

### Repository Structure: Monorepo

PCT uses a single repository with co-located backend and frontend directories. No monorepo tooling (Nx, Turborepo) — just two directories with their own build tools.

```
pct/
  backend/
    pyproject.toml              # Python deps, Ruff config, pytest config
    src/pct/                    # FastAPI app, Pydantic models, agent providers
    tests/                      # pytest (unit + integration)
  frontend/
    package.json                # Node deps, scripts
    src/                        # React app, components, hooks, stores
    tests/                      # Vitest (unit + component)
  playwright/                   # E2E tests (span both backend + frontend)
  docs/                         # Specs, object model, tech spec
  pct.yaml                      # Project configuration (checked in)
  pct-admin/                    # Specs, tasks, feature definitions (checked in)
  .pct/                         # Execution artifacts, RAG, chat history (git-ignored)
  work/                         # Task output artifacts
```

**Rationale:**
- **Tightly coupled product** — frontend TypeScript types mirror backend Pydantic models. API and WebSocket schema changes are atomic (one commit, one PR).
- **Single CI pipeline** — backend tests, frontend tests, and Playwright E2E run together.
- **Ships together** — PCT is local-first, frontend and backend are deployed as one unit. No independent release cadences.
- **Solo/small team** — no cross-repo coordination overhead.

**What doesn't live here:** Monorepo tooling like Nx or Turborepo is for multi-package JS monorepos with complex dependency graphs. PCT is just two directories — `pyproject.toml` and `package.json` handle their own builds independently.

### Backend: Python + FastAPI

**Language: Python 3.11+**

Rationale:
- AI/ML ecosystem is Python-native (llama-cpp-python, transformers, sentence-transformers)
- Claude Code CLI is invoked as a subprocess — Python's `asyncio.create_subprocess_exec` handles this well
- Pydantic is Python-native — our task file frontmatter maps directly to Pydantic models
- User's original vision specified Python

**Framework: FastAPI**

Rationale:
- **Async-native** — critical for concurrent agent execution (multiple agents running in parallel, each streaming output)
- **WebSocket support built-in** — needed for real-time agent streaming and kanban updates
- **Pydantic integration** — request/response validation uses the same models as our file format
- **Lightweight** — no ORM, no admin panel, no batteries we don't need
- Alternatives considered:
  - Flask: no native async, WebSocket requires extensions
  - Django: too heavy, ORM-centric, wrong fit for file-based storage
  - Litestar: viable but smaller ecosystem

**ASGI Server: Uvicorn**

Standard for FastAPI. Handles WebSocket connections and async concurrency.

### Frontend: React + TypeScript + Vite

**React 18+ with TypeScript**

Rationale:
- User specified React
- TypeScript for type safety across the task/kanban data model
- React 18's concurrent features for smooth kanban updates during agent streaming

**Build tool: Vite**

Fast dev server, HMR, simple config. No reason to use webpack in 2026.

**Key libraries:**

| Purpose | Library | Rationale |
|---------|---------|-----------|
| UI component library | `Ant Design (antd)` | Full-featured, enterprise-grade component library. Dense layout with less whitespace than Material alternatives. Strong table, form, and navigation components. |
| Data grid | `AG Grid` | Gold standard for complex data grids — sorting, filtering, grouping, row virtualization, 100k+ row support. Community edition covers most needs; Enterprise adds pivoting, row grouping, Excel export. |
| Icons | `@ant-design/icons` | 831 icons, tightly integrated with Ant Design theming. No need for react-icons — avoids redundant dependency. |
| Forms | `Ant Design Form` | Built-in form system, native integration with all Ant Design components. Has known performance issues on very large forms (100+ fields), but PCT's forms are small configuration-oriented screens — not a concern. Avoids an extra dependency. |
| Rich text / Markdown editing | `TipTap` + `@tiptap/extension-markdown` | For editing specs and task descriptions. Native bidirectional Markdown conversion, modular architecture (50-70KB), excellent React integration via `@tiptap/react`. Alternatives considered: Lexical (Meta) — smaller core but pre-1.0, requires custom Markdown work; Slate — slower maintenance; MDXEditor — 851KB bundle, overkill. |
| Markdown rendering (read-only) | `react-markdown` | For displaying specs, agent output, **and artifact text previews** in the task detail panel. TipTap is used for editing; react-markdown for lightweight read-only rendering. |
| Kanban drag-and-drop | `@hello-pangea/dnd` | Maintained fork of react-beautiful-dnd (which is deprecated). Accessible, smooth, supports horizontal + vertical lists for our columns + swimlanes. |
| Routing | `React Router` | Industry standard, simple and familiar. PCT has ~5 top-level routes (Kanban, Planning Chat, Config, Feedback/Training, Task Detail). No need for TanStack Router's type-safe routing on an app this simple. |
| State management (client) | `Zustand` | Lightweight, no boilerplate. Manages client-only state: kanban drag state, UI state, WebSocket-driven real-time updates. |
| State management (server) | `TanStack Query` | Handles all REST data fetching — automatic caching, deduplication, background refetch, loading/error states. Zustand manages client-only state; TanStack Query manages server state (initial data loads, config reads, task fetches). Clear separation of concerns. |
| HTTP client | `Axios` | Request/response interceptors (auth headers, error normalization), automatic JSON parsing, request cancellation. Paired with TanStack Query — Axios handles the transport, TanStack Query handles caching and state. |
| WebSocket client | `native WebSocket` + reconnect wrapper | No need for socket.io overhead. We control both ends. A small wrapper handles reconnection. Real-time data flows through WebSocket → Zustand; REST data flows through Axios → TanStack Query. |
| Image gallery / lightbox | `yet-another-react-lightbox` | For the Image Gallery Modal in the Chat Interface (fullscreen viewer with left/right navigation, keyboard/touch support). Plugin architecture provides Thumbnails, Fullscreen, and Zoom out of the box. Custom toolbar button API (`toolbar.buttons` prop + `IconButton`/`createIcon` helpers) allows adding PCT-specific "Refine" and "Accept" action buttons. TypeScript built-in, ~200K weekly downloads, actively maintained. |
| Code diff view | `react-diff-viewer` | For code review stage — showing what the agent changed. |
| Date handling | `Day.js` | Ant Design's default date library. Lightweight (2KB), immutable API, Moment.js-compatible interface. |

**UI Guidelines:**

*Theming — compact density:*
Ant Design ships a `compact` theme algorithm that reduces padding, margins, and font sizes globally. PCT uses this as the base theme to minimize whitespace. Additional token overrides tighten spacing further where needed (e.g., card padding, table row height). Theme tokens are configured once in the top-level `<ConfigProvider>` and inherited by all components.

```tsx
import { ConfigProvider, theme } from 'antd';

<ConfigProvider theme={{
  algorithm: theme.compactAlgorithm,
  token: {
    // further density overrides as needed
  }
}}>
  <App />
</ConfigProvider>
```

*Ant Design Table vs AG Grid boundary:*
Use Ant Design's `<Table>` for simple, read-only or lightly interactive lists — config tables, task lists, log entries, anything under ~100 rows with basic sorting/filtering. Use AG Grid for heavy data interaction — execution history browser, training data curation (F7), RAG result inspection, and any view requiring grouping, pivoting, inline editing, or 1000+ rows. AG Grid's theme should be aligned with the Ant Design compact theme for visual consistency.

*Form strategy:*
Ant Design's built-in `<Form>` and `<Form.Item>` handle state, validation, layout, and error display. PCT's forms are small (config pages, task editing, agent setup) — well within Ant Design Form's performance comfort zone.

*Data flow architecture:*
Two clear data paths — no overlap:
- **REST data** (initial loads, config, task CRUD): `Axios → TanStack Query → components`. TanStack Query owns caching, loading states, and refetch logic.
- **Real-time data** (agent streaming, kanban updates, stage transitions): `WebSocket → Zustand → components`. Zustand owns the live state that changes frequently via push updates.

### Frontend Architecture Notes

**Task Detail Panel architecture**: The chat functionality is extracted into a `usePlanningChat` custom hook (`frontend/src/hooks/usePlanningChat.ts`), enabling the TaskDetailPanel to wire up three independent UI sections (context window, input, artifact output) from a single shared state source. This decoupling allows cross-section interactions (e.g., image refine → input pre-fill) without tight component coupling. The `PlanningChat` component uses `usePlanningChat` internally and retains its backwards-compatible API for standalone usage (e.g., the project planning chat).

### Real-Time Communication: SSE + WebSocket

PCT uses **Server-Sent Events (SSE)** for streaming responses and **WebSocket** for bidirectional real-time updates:

**SSE (Server → Client streaming):**
- Chat message streaming — token-by-token agent responses via `POST /api/chat/sessions/{id}/send` (returns SSE stream)
- Feature analysis streaming — gap analysis and continuity check results via `POST /api/board/features/{id}/gap-analysis` and `/continuity-check`
- Image generation progress — job status polling (REST, not SSE, but serves the same purpose)

SSE was chosen for chat streaming because:
- Each chat response is a discrete request/response cycle — the client sends a message and receives a streaming response
- No persistent connection needed between messages
- Simpler error handling and retry semantics
- Works naturally with REST endpoints (same URL, just returns `text/event-stream`)

**WebSocket (bidirectional, future):**
- Task stage change notifications
- Kanban board real-time updates
- Agent interrupt signals
- Multi-user presence (future)

| Transport | Use Case | Direction |
|-----------|----------|-----------|
| SSE | Chat streaming, analysis streaming | Server → Client |
| REST | All CRUD operations, image gen polling | Bidirectional (request/response) |
| WebSocket | Board updates, interrupts (future) | Bidirectional |

### File Parsing: YAML everywhere

PCT uses **YAML as the single configuration/metadata format** for consistency:
- Task files (`.md`): YAML frontmatter parsed by `python-frontmatter`
- Config files (`pct.yaml`): plain YAML parsed by `PyYAML`
- Feature metadata (`metadata.yaml`): plain YAML parsed by `PyYAML`
- Agent configs (`~/.pct/curation/agent_configs/*.yaml`): plain YAML parsed by `PyYAML`

The only exception is **streaming logs** (`agent_log.jsonl`, `planning-*.jsonl`) which use JSONL (JSON Lines) — an append-only format suited for real-time log capture where each line is an independent record.

`python-frontmatter` depends on `PyYAML`, so both parsers come from a single dependency.

```python
import frontmatter
import yaml

# Task files: YAML frontmatter + Markdown body
post = frontmatter.load("define-data-models.md")
# post.metadata = {"id": "001", "status": "code-review", ...}
# post.content = "# Define Data Models\n\n## Spec\n..."

# Config/metadata files: plain YAML
with open("pct.yaml") as f:
    config = yaml.safe_load(f)
```

### RAG: LanceDB

**LanceDB** for vector storage and similarity search.

Rationale:
- **Disk-native** — data stored in Lance columnar files on disk, memory-mapped for reads. No RAM ceiling — unlike ChromaDB whose HNSW index must fit in memory and collapses under swap pressure.
- **Pydantic-native** — `LanceModel` extends Pydantic `BaseModel`. Define schemas as Pydantic models, query results cast back to Pydantic via `.to_pydantic()`. This matches our entire data layer — zero mapping code.
- **SQL WHERE filtering** — filter with familiar SQL syntax: `.where("feature_id = 'f1-core-server' AND outcome = 'rejected'")`. No custom DSL to learn.
- **Lightweight** — ~50MB installed (Rust core + PyArrow). Lightest of the three finalists.
- **Embedding functions** — built-in support for sentence-transformers, OpenAI, and custom embedding functions. Auto-embeds on insert.
- Alternatives evaluated:
  - ChromaDB: most popular but RAM-bound (HNSW index must fit in memory), custom filter DSL, no Pydantic integration, no aggregation
  - txtai: most powerful queries (full SQL + hybrid search) but pulls in PyTorch + full HF stack (~2GB+), overkill dependency weight
  - FAISS: fastest raw search but no metadata filtering, no persistence, requires building everything yourself
  - Qdrant: requires separate server process — against local-first philosophy

**Schema:** The minimal LanceDB schema (`path`, `text`, `vector`) is defined in this tech spec (Section 5 — RAG Pipeline). Image generation session metadata (`ImageSession`, `ImageRound`, `GeneratedImage`) is defined in the Object Model §9.

**Usage example:**
```python
# Add
table.add([TaskDocument(task_id="define-data-models", feature_id="f1-core-server", ...)])

# Query: find similar rejected tasks for this feature
results = (table.search(query_vector)
    .where("feature_id = 'f1-core-server' AND outcome = 'rejected'")
    .limit(5)
    .to_pydantic(TaskDocument))
```

**Embedding model:** `all-MiniLM-L6-v2` via sentence-transformers (runs locally, fast, 384-dimensional output, good quality for retrieval). Can be swapped for API-based embeddings if preferred.

**Storage location:** `$PCT_PROJECT_ROOT/.pct/rag/` — Lance files live alongside other execution state in the git-ignored `.pct/` directory, never committed to the project repo.

### Agent Execution

**Claude Code CLI (primary — stub):**
- Invoked via `asyncio.create_subprocess_exec`
- PCT streams stdout/stderr in real-time via SSE to the frontend
- PCT captures the full transcript to the execution state directory
- Interrupt = send SIGTERM/SIGINT to the subprocess
- *Note: Currently a stub (`NotImplementedError`) — implementation pending*

**Local LLM (active):**
- `llama-cpp-python` for direct inference
- Loaded in a separate process or thread pool to avoid blocking the FastAPI event loop
- Same streaming interface as CLI — PCT normalizes the output
- Supports tool calling via text content parsing (fallback mechanism)
- GPU layer offloading via `n_gpu_layers` parameter
- Configurable temperature and context length

**HuggingFace models:**
- Models downloaded from HuggingFace Hub on demand
- Download status tracked in model registry (pending → downloading → ready → error)
- Supports `.gguf` and `.safetensors` formats
- Auto-discovery scans `{project_root}/models` and `~/.pct/models` directories

**Image Generation (HuggingFace Diffusers):**
- Uses `diffusers` library with Stable Diffusion models (default: `sd-legacy/stable-diffusion-v1-5`)
- Supports text-to-image and image-to-image generation
- Generates 4 images per round with configurable parameters
- Asynchronous job-based execution — generation runs in background, status polled via REST
- Session metadata persisted per task at `{artifact_work_dir}/images/session.json` (where `artifact_work_dir` is the task's work directory, e.g. `work/{feature_id}/{task_id}/`)
- Images stored as PNG files in `{artifact_work_dir}/images/`
- Text artifacts stored at `{artifact_file_path}` (the feature document file)

**User/Manual agent:**
- PCT presents the task spec in the UI and waits
- User marks the task complete (or rejects/modifies)
- No subprocess — just a state transition

**Tool System:**
- Backend provides a tool registry with available tools: `bash`, `file_tools`, `read_tool`, `search_tool`, `todo_tool`
- Tools are provided to agents during execution via a global singleton registry
- Created lazily from the project root

**Agent abstraction interface:** The `AgentProvider` protocol and provider implementations are defined in this tech spec (Section 4 — Agent Abstraction Layer). All providers implement the same `execute()` / `interrupt()` interface. PCT doesn't care which backend is executing — it assembles context, calls `execute()`, streams output, and stores results.

### Agent Concurrency Pool

PCT enforces configurable concurrency limits using Python's `asyncio.Semaphore` — one per provider type (remote API, local GPU). Caps how many agents of each type can run simultaneously. Defaults: 2 remote, 1 local. Jobs are submitted as `asyncio.Task` instances; each acquires the appropriate semaphore before execution. See §4.5 for the full `AgentPool` implementation.

```python
class AgentPool:
    def __init__(self, remote_limit: int = 2, local_limit: int = 1):
        self.semaphores = {
            "remote": asyncio.Semaphore(remote_limit),
            "local": asyncio.Semaphore(local_limit),
        }

    def submit(self, job: AgentJob) -> asyncio.Future[AgentResult]:
        """Submit job for execution. Returns a future for the result."""
        return asyncio.ensure_future(self._run_job(job))

    async def _run_job(self, job: AgentJob) -> AgentResult:
        """Acquire the provider-type semaphore, then execute."""
        async with self.semaphores[job.provider_type]:
            return await job.provider.execute(job.task, job.context, job.on_output)
```

Limits are configurable per project via `pct.yaml` and the Project Configuration page (F10).

### Context Manager

An LLM-powered tool that handles intelligent context summarization and compression. Sits in the execution pipeline between context assembly (gathering raw materials) and agent invocation (sending the prompt).

**Responsibilities:**
- Summarize older retry attempts (beyond the latest 2) into concise lessons-learned
- Compress/prioritize RAG results to fit within the target model's token budget
- Produce a coherent assembled context that preserves the most relevant information
- Available as a **tool/skill** that agents can call mid-execution to request additional context or re-summarize

**Implementation:**
- Implements the same `AgentProvider` interface as other agents — it's an LLM call with a specialized prompt
- The Agent Execution Engine calls it as a pre-processing step before each agent invocation
- Also registered as a tool in the agent's tool belt so agents can invoke it directly during execution

**Model configuration:**
- Uses a configurable model, independent of the task agent's model
- **Remote models**: guided via prompt skills (versioned prompt templates in `~/.pct/curation/prompt_templates/`, e.g., `context-summarize.md`)
- **Local models**: can be fine-tuned with LoRA trained on project-specific summarization examples (positive: good summaries that led to successful task completions; negative: summaries that lost critical context)
- A lightweight/fast model is preferred since this runs before every agent invocation — latency matters

```python
class ContextManager:
    """Pre-processes assembled context to fit within model token limits."""

    def __init__(self, provider: AgentProvider, token_budget: int):
        self.provider = provider
        self.token_budget = token_budget

    async def prepare_context(self, raw_context: RawContext) -> AssembledContext:
        """Summarize and compress raw context to fit within token budget.

        Called by the Agent Execution Engine before each agent invocation.
        """
        # Specs always included verbatim (tier 1)
        base = raw_context.project_spec + raw_context.feature_spec + raw_context.task_spec
        remaining_budget = self.token_budget - count_tokens(base)

        # Summarize old retry history (tier 2)
        retry_context = await self._summarize_retries(
            raw_context.retry_history, remaining_budget
        )

        # Rank and fit RAG results (tier 3)
        rag_context = await self._compress_rag(
            raw_context.rag_results, remaining_budget - count_tokens(retry_context)
        )

        return AssembledContext(base=base, retries=retry_context, rag=rag_context)
```

The Context Manager's summarization quality improves over time as training data accumulates from project usage — making it a core part of PCT's learning loop.

### Git: subprocess calls to git CLI

Rationale:
- GitPython has known issues with Windows and worktrees
- Direct `git` CLI calls via `asyncio.create_subprocess_exec` are more reliable
- We need worktree support (`git worktree add/remove`) which is better tested via CLI
- Simple wrapper functions, not a full abstraction

```python
async def create_worktree(project_path: Path, branch: str, worktree_path: Path):
    await run_git(project_path, "worktree", "add", "-b", branch, str(worktree_path))

async def merge_branch(project_path: Path, branch: str) -> MergeResult:
    result = await run_git(project_path, "merge", branch, "--no-ff")
    return MergeResult(success=result.returncode == 0, output=result.stdout)
```

### LoRA Training (future)

Not a priority for initial build but the ecosystem:
- **unsloth** — fast LoRA fine-tuning, good for local execution
- **peft + transformers** — Hugging Face standard, more flexible
- PCT collects training data in `~/.pct/curation/training_data/`, then kicks off training as a background process
- Trained LoRAs are stored in `~/.pct/curation/loras/` and referenced by agent configs

### Testing

**Backend (Python):**

| Purpose | Library | Rationale |
|---------|---------|-----------|
| Test runner | `pytest` | Standard for Python. Async support via `pytest-asyncio`. |
| Async test support | `pytest-asyncio` | Required for testing async FastAPI endpoints and WebSocket handlers. |
| API test client | `httpx` | FastAPI's recommended test client (`AsyncClient`). Supports async, replaces `requests` in test context. |
| Coverage | `pytest-cov` | Coverage reporting for CI and local development. |

**Frontend (React + TypeScript):**

| Purpose | Library | Rationale |
|---------|---------|-----------|
| Test runner | `Vitest` | Native Vite integration, Jest-compatible API, shares Vite's transform pipeline. No reason to use Jest with a Vite project. |
| Component testing | `@testing-library/react` | Standard for React — tests user-facing behavior, not implementation details. |
| API mocking | `MSW` (Mock Service Worker) | Intercepts network requests at the service worker level. Works with both Axios and WebSocket. Cleaner than mocking Axios directly — tests don't couple to the HTTP client. |
| E2E testing | `Playwright` | Multi-browser, fast parallel execution, no vendor lock-in. Preferred over Cypress for local-first apps — no paid dashboard dependency, better async handling. |

### Linting & Formatting

**Backend (Python): `Ruff`**

Ruff replaces Black, Flake8, isort, pycodestyle, and dozens of other tools — single binary, written in Rust, 10-100x faster. Configured via a single `[tool.ruff]` section in `pyproject.toml`.

- `ruff check` — linting (800+ rules covering Flake8, isort, pydocstyle, pyupgrade, and more)
- `ruff format` — formatting (Black-compatible output)
- `ruff check --fix` — auto-fix linting violations

```toml
# pyproject.toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]  # errors, pyflakes, isort, pyupgrade, bugbear, simplify
```

**Frontend (TypeScript): `ESLint` + `Prettier`**

ESLint handles linting (code quality, unused vars, import issues), Prettier handles formatting (whitespace, semicolons, quotes). They don't overlap — Prettier formats, ESLint catches bugs.

- `eslint` + `@typescript-eslint/eslint-plugin` — TypeScript-aware linting
- `prettier` — opinionated formatting
- `eslint-config-prettier` — disables ESLint rules that conflict with Prettier

```json
// .eslintrc.json (minimal)
{
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
    "prettier"
  ]
}
```

### Logging: `loguru`

Zero-config logging. Colored console output for development, file rotation built-in. PCT is local-first — logs are read in a terminal, not shipped to a log aggregator. No reason for `structlog`'s structured JSON or the boilerplate of stdlib `logging`.

```python
from loguru import logger

logger.info("Agent started", task_id="001", agent="claude-code")
```

Log level is configured via the `PCT_LOG_LEVEL` environment variable (see Environment Configuration below).

### Environment Configuration

Three layers of configuration, each with a distinct purpose:

| Layer | What | Where | Managed by |
|-------|------|-------|------------|
| **Project config** | Workflow stages, agents, concurrency, project metadata | `pct.yaml` in project repo | PCT UI (F10) and planning agent |
| **Environment config** | Host, port, log level, API keys, CORS origin | `.env` file in repo root (git-ignored) | User, per machine |
| **Frontend env** | Backend API URL | `.env` via Vite's `VITE_` prefix | Vite built-in (`import.meta.env`) |

**Backend: `pydantic-settings`**

Natural fit — already using Pydantic everywhere. Reads from `.env` files and environment variables, validates with Pydantic models.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    cors_origin: str = "http://localhost:5173"    # Vite dev server
    secret_key: str = "change-me-in-production"   # JWT signing key
    access_token_expire_minutes: int = 1440       # 24 hours
    google_client_id: str = ""                    # optional Google OAuth
    project_root: str                             # required: project directory
    registries_dir: str = ""                      # optional: defaults to ~/.pct/registries
    user_data_dir: str = ""                       # optional: user storage location

    model_config = SettingsConfigDict(env_file=".env", env_prefix="PCT_")
```

**Frontend:** Vite handles this natively — `VITE_` prefixed vars in `.env`, accessed via `import.meta.env.VITE_API_URL`. No extra library.

### Dependency Summary

**Backend (Python):**
```
fastapi
uvicorn[standard]
python-frontmatter
pydantic >= 2.0
lancedb
sentence-transformers
llama-cpp-python          # local LLM inference
sse-starlette             # Server-Sent Events for streaming
diffusers                 # HuggingFace image generation
torch                     # PyTorch (required by diffusers)
transformers              # HuggingFace model hub
websockets
aiofiles
pyyaml
tiktoken                     # token counting for remote API models
loguru
pydantic-settings
pyjwt                     # JWT token creation/verification
bcrypt                    # password hashing
google-auth               # optional: Google OAuth token verification
aiosmtplib                # async SMTP for email notifications (F13)
ruff                      # dev
pytest                    # dev
pytest-asyncio            # dev
httpx                     # dev
pytest-cov                # dev
```

**Frontend (Node/TypeScript):**
```
react, react-dom
typescript
vite
react-router-dom
antd
@ant-design/icons
ag-grid-react, ag-grid-community
@tanstack/react-query
axios
@tiptap/react, @tiptap/starter-kit, @tiptap/extension-markdown
@hello-pangea/dnd
zustand
react-markdown
react-diff-viewer-continued
yet-another-react-lightbox
dayjs
@xyflow/react             # graph visualization for PERT chart (F12)
@dagrejs/dagre            # DAG layout algorithm for PERT chart
eslint                    # dev
@typescript-eslint/eslint-plugin  # dev
prettier                  # dev
eslint-config-prettier    # dev
vitest                    # dev
@testing-library/react    # dev
msw                       # dev
playwright                # dev
```

### Local Dev Setup

No Docker. Run backend and frontend directly:
- Backend: `uvicorn` (via `pyproject.toml` script)
- Frontend: `vite dev`
- No orchestration needed — two terminal windows.

### CI (low priority)

GitHub Actions when needed. Three jobs: backend (ruff + pytest), frontend (eslint + prettier + vitest), e2e (playwright). Not critical for initial development — PCT is local-first with a small team. Add when the project stabilizes.

---

## 3. API Design

### 3.1 Overview

All API endpoints live under `/api/`. Authentication uses JWT bearer tokens. Long-running operations (chat streaming, feature analysis) use Server-Sent Events (SSE). WebSocket support is planned for real-time board updates and agent interrupt signals but is not yet implemented.

**Transport summary:**

| Transport | Use Case | Direction |
|-----------|----------|-----------|
| REST (JSON) | All CRUD operations, image gen polling | Request → Response |
| SSE | Chat streaming, gap analysis, continuity check, impact analysis | Server → Client |
| WebSocket | Board updates, agent interrupts, notifications (future) | Bidirectional |

### 3.2 Authentication

PCT uses JWT bearer tokens for API authentication. The auth module (`pct.auth`) provides:

- **Password auth** — `bcrypt` password hashing with `pyjwt` HS256 token generation. Tokens expire after 24 hours (configurable via `PCT_ACCESS_TOKEN_EXPIRE_MINUTES`).
- **Google OAuth** — optional, enabled when `PCT_GOOGLE_CLIENT_ID` is configured. Verifies Google ID tokens via `google-auth` library and issues a PCT JWT on success.
- **User storage** — JSON file at `~/.pct/users/users.json` (or `PCT_USER_DATA_DIR`). Not a database — PCT is local-first and single-user in practice.
- **Request flow** — `Authorization: Bearer <token>` header → `get_current_user()` FastAPI dependency extracts email from JWT payload.

```python
# pct.auth.service
def create_access_token(data: dict) -> str:
    payload = {**data, "exp": datetime.utcnow() + timedelta(minutes=expire)}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
```

### 3.3 Endpoint Catalog

Endpoints are grouped by router prefix. All endpoints except `/api/health` and `/api/auth/*` require JWT authentication.

**Health**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check (no auth) |

**Auth (`/api/auth`)**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/register` | Create user (email + password), returns JWT |
| POST | `/login` | Authenticate, returns JWT |
| POST | `/google` | Google OAuth token exchange, returns JWT |
| GET | `/me` | Get current user profile |

**Board (`/api/board`)**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Full board state (all features + tasks) |
| GET | `/artifact-types` | Configured artifact types map |
| GET | `/features` | List features |
| POST | `/features` | Create feature |
| GET | `/features/{id}` | Get feature |
| PATCH | `/features/{id}` | Update feature metadata |
| DELETE | `/features/{id}` | Delete feature |
| POST | `/features/{id}/suspend` | Suspend feature (F8) |
| POST | `/features/{id}/resume` | Resume feature (F8) |
| GET | `/backlog` | List backlog features |
| POST | `/backlog/{id}/activate` | Activate backlog feature |
| GET | `/features/{id}/tasks` | List tasks for feature |
| POST | `/features/{id}/tasks` | Create task |
| GET | `/features/{fid}/tasks/{tid}` | Get task |
| PUT | `/features/{fid}/tasks/{tid}` | Update task |
| DELETE | `/features/{fid}/tasks/{tid}` | Delete task |
| POST | `/features/{fid}/tasks/{tid}/move` | Move task (stage change) |
| POST | `/tasks/reassign` | Cross-feature task reassignment |
| GET | `/features/{fid}/tasks/{tid}/artifact` | Read task artifact |
| GET | `/features/{fid}/tasks/{tid}/files` | List artifact files |
| PUT | `/features/{fid}/tasks/{tid}/artifact` | Write task artifact |
| POST | `/features/{id}/gap-analysis` | Stream gap analysis (SSE) |
| POST | `/features/{id}/continuity-check` | Stream continuity check (SSE) |
| POST | `/features/{id}/impact-analysis` | Stream impact analysis (SSE) — *planned* |

**Chat (`/api/chat`)**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sessions` | List chat sessions |
| POST | `/sessions` | Create session |
| GET | `/sessions/default` | Get or create default session |
| GET | `/sessions/{id}` | Get session |
| GET | `/sessions/{id}/messages` | List messages |
| POST | `/sessions/{id}/send` | Send message + stream response (SSE) |
| PUT | `/sessions/{id}/messages/{mid}` | Update message (role, content, included) |
| DELETE | `/sessions/{id}/messages/{mid}` | Delete message |
| DELETE | `/sessions/{id}/messages/{mid}/truncate` | Delete message and all subsequent |

**Config (`/api/config`)**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/project/status` | Check if project is initialized |
| GET | `/project` | Load project config from `pct.yaml` |
| PUT | `/project` | Save project config |
| POST | `/project/reindex` | Rebuild RAG index (F10) |
| GET | `/models` | List model registry entries |
| POST | `/models` | Create model entry |
| GET | `/models/{id}` | Get model |
| PUT | `/models/{id}` | Update model |
| POST | `/models/{id}/download` | Download HuggingFace model |
| DELETE | `/models/{id}` | Delete model |
| GET | `/loras` | List LoRA entries |
| POST | `/loras` | Create LoRA entry |
| GET | `/loras/{id}` | Get LoRA |
| PUT | `/loras/{id}` | Update LoRA |
| DELETE | `/loras/{id}` | Delete LoRA |
| GET | `/agents` | List agents |
| POST | `/agents` | Create agent |
| GET | `/agents/{id}` | Get agent |
| PUT | `/agents/{id}` | Update agent |
| DELETE | `/agents/{id}` | Delete agent |
| GET | `/workflow-stages` | List workflow stages |
| PUT | `/workflow-stages` | Save workflow stages |
| GET | `/template-variables` | List template variables |
| PUT | `/template-variables` | Save template variables |
| GET | `/artifact-types` | List artifact types |
| PUT | `/artifact-types` | Save artifact types |
| GET | `/browse-files` | File browser (query param `path`) |

**Image Generation (`/api/imagegen`)**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/generate` | Start async image generation job |
| GET | `/jobs/{job_id}` | Poll job status and progress |
| GET | `/{fid}/{tid}/session` | Get image session metadata |
| POST | `/{fid}/{tid}/select` | Select image for refinement |
| GET | `/{fid}/{tid}/images/{filename}` | Serve generated image file |

**Notifications (`/api/notifications`) — *planned***

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List notification events (F13) |
| POST | `/{id}/acknowledge` | Acknowledge a notification |
| POST | `/acknowledge-all` | Acknowledge all notifications |

**PERT (`/api/board`) — *planned***

| Method | Path | Description |
|--------|------|-------------|
| GET | `/features/{id}/pert` | Feature-scoped dependency graph data (F12) |
| GET | `/pert` | Project-wide dependency graph data (F12) |

**Training (`/api/training`) — *planned***

| Method | Path | Description |
|--------|------|-------------|
| GET | `/flags` | List training flags (F7) |
| POST | `/flags` | Create training flag |
| PUT | `/flags/{id}` | Update training flag |
| DELETE | `/flags/{id}` | Delete training flag |
| GET | `/datasets` | List datasets |
| POST | `/datasets` | Create dataset |
| POST | `/jobs` | Start training job |
| GET | `/jobs/{id}` | Get training job status |
| GET | `/evaluations` | List evaluation sessions |
| POST | `/evaluations` | Create evaluation session |

### 3.4 SSE Event Format

Streaming endpoints (chat send, gap analysis, continuity check) return `text/event-stream` responses. Each event is a JSON object on a `data:` line, followed by a blank line:

```
data: {"type": "token", "content": "The"}

data: {"type": "token", "content": " answer"}

data: {"type": "done", "message_id": "msg-123"}

```

**Event types:**

| Type | Payload | Emitted by |
|------|---------|------------|
| `token` | `{content: string}` | Chat streaming, analysis streaming |
| `done` | `{message_id?: string}` | All SSE endpoints on completion |
| `error` | `{message: string}` | All SSE endpoints on failure |

**Client implementation note:** SSE endpoints use `POST` with JSON request bodies, which means the browser-native `EventSource` API cannot be used (it only supports `GET`). The frontend uses `fetch()` with a `ReadableStream` reader to parse the `text/event-stream` response manually.

### 3.5 WebSocket Events (Future)

Planned WebSocket connection at `ws://localhost:8000/api/ws` for bidirectional real-time updates. Message format:

```json
{
  "event": "task.stage_changed",
  "data": {
    "feature_id": "f1-core-server",
    "task_id": "define-data-models",
    "from_stage": "implement",
    "to_stage": "code-review"
  }
}
```

**Planned event types:**

| Event | Direction | Description |
|-------|-----------|-------------|
| `task.stage_changed` | Server → Client | Task moved between workflow stages |
| `task.execution_started` | Server → Client | Agent began executing on a task |
| `task.execution_completed` | Server → Client | Agent finished (success or error) |
| `feature.stage_changed` | Server → Client | Feature lifecycle transition |
| `agent.interrupt` | Client → Server | User requests agent interruption |
| `notification.new` | Server → Client | New notification event (F13) |

### 3.6 DAG Validation

The `blocked_by` graph must be acyclic at all times. PCT validates on every task save using a DFS-based topological sort with cycle detection:

```python
def validate_dag(tasks: list[Task]) -> list[str] | None:
    """Validate that blocked_by relationships form a DAG.

    Returns None if valid, or a list of task IDs forming the cycle.
    Uses iterative DFS with three-color marking:
      WHITE = unvisited, GRAY = in current path, BLACK = fully processed.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {t.id: WHITE for t in tasks}
    parent = {}

    adjacency = {}
    for task in tasks:
        adjacency[task.id] = [
            resolve_link(link) for link in task.blocked_by
        ]

    for start in adjacency:
        if color[start] != WHITE:
            continue
        stack = [start]
        while stack:
            node = stack[-1]
            if color[node] == WHITE:
                color[node] = GRAY
                for neighbor in adjacency.get(node, []):
                    if color.get(neighbor) == GRAY:
                        # Cycle found — reconstruct path
                        cycle = [neighbor, node]
                        p = parent.get(node)
                        while p != neighbor:
                            cycle.append(p)
                            p = parent.get(p)
                        return list(reversed(cycle))
                    if color.get(neighbor) == WHITE:
                        parent[neighbor] = node
                        stack.append(neighbor)
            else:
                stack.pop()
                color[node] = BLACK

    return None  # Valid DAG
```

The cycle detection covers both within-feature and cross-feature `blocked_by` references. WikiLinks are resolved to `(feature_id, task_id)` tuples before graph construction.

### 3.7 WikiLink Resolution

WikiLinks use the syntax `[[feature_id#task_id]]` (or `[[feature_id]]` for feature-level references), mirroring the `work/` directory structure. The `pct.board.wikilinks` module handles extraction and resolution:

```python
# Extraction: regex-based parsing
WIKILINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")

def extract_wikilinks(text: str) -> list[str]:
    """Extract [[...]] link targets from markdown text."""
    return WIKILINK_RE.findall(text)
```

**Resolution strategy (dual):**

1. **Structural ID match** — if the link target contains `#`, split into `feature_id` and `task_id` and look up directly by ID.
2. **Title-matching fallback** — if no `#` separator, search all features and tasks by case-insensitive title match. Prefers exact matches over substrings.

Resolution is used by:
- **Context builder** — resolving `cross_refs` and `blocked_by` entries to load referenced artifacts into agent context.
- **Artifact rendering** — WikiLinks in markdown are displayed as clickable links in the frontend.
- **DAG validation** — resolving `blocked_by` entries to build the dependency graph.

---

## 4. Agent Abstraction Layer

### 4.1 AgentProvider Protocol

All agent backends implement the same async protocol, defined in `pct.agent.protocols`:

```python
@runtime_checkable
class AgentProvider(Protocol):
    """Common interface for agent execution backends."""

    async def execute(
        self,
        messages: list[dict[str, str]],
        on_token: Callable[[str], Awaitable[None]] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentResult: ...

    async def interrupt(self) -> None: ...
```

**Contract:**
- `execute()` receives a list of chat messages (OpenAI format), an optional streaming callback, and an optional list of tool definitions. Returns an `AgentResult` containing the output text, token counts, tool calls, duration, and outcome status.
- `on_token` is called for each streamed token, enabling real-time SSE delivery to the frontend.
- `interrupt()` signals the provider to stop execution. The provider completes its current generation step and returns a partial result.

**Supporting types:**

```python
class AgentResult(BaseModel):
    outcome: TaskOutcome = TaskOutcome.IN_PROGRESS
    output: str = ""
    messages: list[LLMMessage] = []
    tool_calls: list[ToolCall] = []
    tokens_input: int = 0
    tokens_output: int = 0
    duration_seconds: float = 0.0
    error: str | None = None
```

### 4.2 Provider Implementations

| Provider | Module | Backing Library | Status | Streaming | Tool Calls |
|----------|--------|----------------|--------|-----------|------------|
| `LocalLLMProvider` | `pct.agent.providers.local_llm` | `llama-cpp-python` | Active | Yes (token callback) | Yes (text-parsed fallback) |
| `ClaudeCodeProvider` | `pct.agent.providers.claude_code` | `asyncio.create_subprocess_exec` | Stub (`NotImplementedError`) | Planned (stdout streaming) | Planned (native) |
| `UserProvider` | — | None | Active | N/A | N/A |
| `ImageGenProvider` | `pct.imagegen` | `diffusers` | Active | N/A (poll-based) | N/A |

**Provider resolution** is handled by `pct.chat.provider_factory`:

```python
def resolve_provider(agent_id: str) -> tuple[AgentProvider, AgentConfig]:
    """Look up AgentConfig from pct.yaml and instantiate the matching provider."""
```

The factory reads the agent's `model_id` → `ModelRegistryEntry.provider_type` to select the correct backend class.

### 4.3 Tool System

Agents can invoke tools during execution. The tool system is defined in `pct.agent.tools`:

**Tool protocol:**

```python
class Tool(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def definition(self) -> dict[str, Any]: ...  # OpenAI function schema

    async def execute(self, arguments: str) -> str: ...  # JSON args → text
```

**ToolRegistry:**

```python
class ToolRegistry:
    def register(self, tool: Tool) -> None
    def get_definitions(self) -> list[dict]   # Passed to LLM as tool schemas
    async def execute(self, name: str, arguments: str) -> str
```

**Registered tools:**

| Tool | Name | Description |
|------|------|-------------|
| `ReadTool` | `read` | Read files (relative to project root) or fetch URLs. Auto-detects source type. |
| `FileTool` | `file` | Write or edit files. Actions: `write` (full content), `edit` (old_text → new_text). Auto-indexes `work/` files into RAG. |
| `SearchTool` | `search` | Combined web search (DuckDuckGo) + RAG semantic search. Returns merged results. |
| `TodoTool` | `todo` | Manage project tasks. Actions: `list`, `get`, `create`, `edit`, `delete`. Reads/writes frontmatter markdown task files. |
| `BashTool` | `bash` | Execute shell commands with a 30-second timeout. Captures stdout + stderr. |

**Tool factory:**

```python
def create_global_registry(project_root: Path, project_id: str) -> ToolRegistry:
    """Instantiate all tools with project context. Lazy singleton."""
```

Tools are provided to agents during execution via the global registry. The registry is created lazily from the project root on first use.

### 4.4 Chat Loop

The core execution function in `pct.agent.chat_loop` manages the interaction between the agent provider and the tool system:

```python
async def execute_chat_turn(
    provider: AgentProvider,
    context: AssembledContext,
    system_prompt: str | None = None,
    on_token: Callable[[str], Awaitable[None]] | None = None,
    timeout_seconds: float | None = None,
    tool_registry: ToolRegistry | None = None,
    max_tool_iterations: int = 10,
) -> AgentResult:
```

**Execution flow:**

1. `build_messages(context, system_prompt)` converts `AssembledContext` into an LLM message list.
2. Call `provider.execute(messages, on_token, tools)`.
3. If the result contains `tool_calls` and a `tool_registry` is provided:
   - Execute each tool call via the registry.
   - Append tool results to the message list.
   - Loop back to step 2 (max 10 iterations by default).
4. When no tool calls remain (or the registry is `None`), return the final `AgentResult`.

The loop handles tool execution errors gracefully — a failed tool returns an error message rather than crashing the loop. Timeout support wraps the entire execution in `asyncio.wait_for()`.

### 4.5 Agent Concurrency Pool

The `AgentPool` in `pct.agent.pool` enforces per-provider-type concurrency limits:

```python
class AgentPool:
    def __init__(self, remote_limit: int = 2, local_limit: int = 1):
        self.semaphores = {
            "remote": asyncio.Semaphore(remote_limit),
            "local": asyncio.Semaphore(local_limit),
        }

    def submit(self, job: AgentJob) -> asyncio.Future[AgentResult]:
        """Submit job for execution. Returns a future for the result."""

    async def _run_job(self, job: AgentJob) -> AgentResult:
        """Acquire the provider-type semaphore, then execute."""
        async with self.semaphores[job.provider_type]:
            return await job.provider.execute(...)
```

Limits are read from `pct.yaml` (`max_remote_agents`, `max_local_agents`) and can be changed at runtime via F10.

---

## 5. RAG Pipeline

### 5.1 Embedding Strategy

PCT uses `sentence-transformers/all-MiniLM-L6-v2` for local embedding generation:

- **Dimensions:** 384
- **Loading:** Lazy-loaded singleton — the model is loaded on first use and reused across all embedding operations.
- **Text truncation:** Input text is truncated to 8192 characters before encoding. This covers the vast majority of task artifacts while keeping embedding time fast.
- **Performance:** Runs on CPU. Embedding a single document takes ~10–50ms depending on length.

The model is used both for indexing (embedding documents into LanceDB) and for querying (embedding search queries at retrieval time).

### 5.2 Storage Schema

**Current minimal schema:**

```python
# LanceDB table: "artifacts"
{
    "path":   str,           # file path relative to project root
    "text":   str,           # file content (first 8192 chars)
    "vector": vector(384),   # all-MiniLM-L6-v2 embedding
}
```

**Target expanded schema** (future — enables filtered queries):

```python
{
    "path":       str,
    "text":       str,
    "vector":     vector(384),
    "feature_id": str | None,    # parent feature
    "task_id":    str | None,    # parent task
    "stage":      str | None,    # workflow stage at indexing time
    "file_type":  str,           # extension (.md, .py, etc.)
    "indexed_at": timestamp,
}
```

The expanded schema will enable SQL WHERE filtering (e.g., `.where("feature_id = 'f1-core-server' AND stage = 'implement'")`) for more targeted retrieval.

**Storage location:** `$PCT_PROJECT_ROOT/.pct/rag/` — LanceDB files live alongside other execution state in the git-ignored `.pct/` directory, never committed to the project repo.

### 5.3 What Gets Indexed

**Indexed:**
- Files under the `work/` directory tree — task artifacts (`main.md`), feature documents, auxiliary files
- Project specification (`pct-admin/project_spec.md`)
- Feature specifications (`pct-admin/active-features/*/feature_spec.md`)
- Supported extensions: `.md`, `.txt`, `.py`, `.yaml`, `.yml`, `.json`, `.rst`

**NOT indexed:**
- Chat history (`.pct/chat_history/`) — conversational process, not durable output
- Worktree contents — agents access their own worktree files directly via the filesystem
- Execution logs (`.pct/execution/`) — raw agent transcripts, too noisy for retrieval
- Binary files (images, PDFs, model weights)
- Files outside the project root

### 5.4 Indexing Triggers

| Trigger | Scope | Implementation |
|---------|-------|----------------|
| Manual reindex (F10) | Full project | `reindex_all()` — drops and rebuilds the entire index |
| After task merge (F5) | Changed files | `git diff --name-only HEAD~1` → `index_file()` per changed file |
| File write by agent | Single file | `FileTool.execute()` calls `index_file()` after writing to `work/` |

Indexing is additive — `index_file()` upserts by path (existing entries are overwritten). Full reindex drops the table and rebuilds from scratch.

### 5.5 Retrieval & Ranking

Retrieval uses LanceDB's built-in vector search:

```python
def rag_search_context(project_id: str, query: str, max_results: int = 5) -> str:
    """Semantic search over indexed artifacts.

    1. Encode query with all-MiniLM-L6-v2
    2. Search LanceDB: table.search(query_vector).limit(max_results)
    3. Format results as context text (path + 500-char snippet per result)
    """
```

**Ranking:** Cosine similarity (LanceDB default distance metric). Results are returned in descending similarity order.

**Result format:** Each result is formatted as a path header followed by a 500-character text snippet:

```
## Related: work/f1-core-server/f1-core-server.md
Define Pydantic models for Project, Feature, Task, Agent, and WorkflowStage.
Models should be persisted to JSON files...
```

**Future:** SQL WHERE metadata filtering (once the expanded schema is implemented) will allow scoped queries like "find similar tasks within the same feature" or "find rejected approaches for this workflow stage."

### 5.6 Context Integration

RAG results are injected into the agent context at two levels:

1. **Chat router level** — when a user sends a message via `POST /api/chat/sessions/{id}/send`, the router performs a RAG search using the user's message as the query. Results are prepended to the system context as a `## World Knowledge (RAG)` section before the message reaches the agent.

2. **Agent tool level** — agents can query RAG mid-execution via the `SearchTool`. This allows agents to pull in additional context beyond what was assembled in the initial prompt — useful when the agent discovers it needs information about a related feature or prior task.

**Data flow:**

```
User message
  → resolve_task_context()     # cross_refs, blocked_by artifacts
  → rag_search_context()       # semantic search over indexed artifacts
  → build system context:
      - Cross-reference artifacts
      - RAG results (## World Knowledge)
      - Artifact type hint
      - Expanded stage prompt
  → execute_chat_turn()        # agent may also call SearchTool
  → SSE stream to frontend
```

---

## 6. Git Worktree Management

### 6.1 Worktree Lifecycle

Git worktrees provide isolation for concurrent agent execution. Each task execution gets its own worktree so agents can modify files without interfering with each other or with the user's main working tree.

```
1. Task dequeued for execution (F4)
   └─→ create_worktree(project_path, branch, worktree_path)

2. Agent executes in worktree
   └─→ CWD = worktree root (transparent to agent)

3. Execution completes
   ├─→ Success: merge back to feature branch → cleanup worktree
   └─→ Failure: preserve worktree for retry/inspection
```

**Metadata storage:** The feature's `metadata.yaml` tracks `worktree_path` and `branch` fields. These are set when a worktree is created and cleared on cleanup.

### 6.2 Branch Naming

| Branch Type | Pattern | Lifetime |
|-------------|---------|----------|
| Feature branch | `feature/{feature_id}` | Long-lived — exists from feature activation to completion |
| Task branch | `feature/{feature_id}/{task_slug}` | Per execution — created in worktree, merged or abandoned |

Task slugs are generated from the task title (lowercased, spaces → hyphens, special characters stripped).

### 6.3 Merge Serialization

Concurrent agents within the same feature can produce merge conflicts if their worktrees are merged simultaneously. PCT serializes merges per feature branch using an `asyncio.Lock`:

```python
# One lock per feature branch — prevents concurrent merge conflicts
_feature_locks: dict[str, asyncio.Lock] = {}

async def merge_task_branch(project_path: Path, feature_id: str, task_branch: str):
    lock = _feature_locks.setdefault(feature_id, asyncio.Lock())
    async with lock:
        result = await run_git(project_path, "merge", task_branch, "--no-ff")
        if result.returncode != 0:
            raise MergeConflictError(result.stderr)
```

Tasks from different features merge into different feature branches, so no cross-feature lock contention occurs.

### 6.4 Conflict Handling

When a merge conflict occurs:

1. **Task state** — `execution_status` set to `error`, `error_details` populated with conflict information.
2. **Notification** — `notification_state` set to `attention` (red card border on Kanban board). If a product notification email is configured, an email alert is sent (F13).
3. **Worktree preserved** — the worktree is not cleaned up, allowing inspection and resolution.

**User resolution options:**

| Option | Behavior |
|--------|----------|
| Manual resolution | User opens the worktree, resolves conflicts, commits, and triggers merge retry |
| Resolution agent | User assigns an LLM agent to resolve the conflict in the preserved worktree (future) |
| Discard and re-execute | User discards the worktree and re-runs the task from scratch |

### 6.5 Cleanup

- **After successful merge:** `git worktree remove <path>` deletes the worktree directory and unregisters it from git.
- **After failure:** Worktree is preserved until the user explicitly retries or discards.
- **Periodic stale cleanup:** On project load, PCT can scan for orphaned worktrees (worktrees whose associated task is no longer in a running state) and offer to clean them up.

### 6.6 Post-Merge Re-indexing

After a successful merge, PCT incrementally updates the RAG index for changed files:

```python
async def post_merge_reindex(project_path: Path, project_id: str):
    """Re-index files changed in the last merge commit."""
    result = await run_git(project_path, "diff", "--name-only", "HEAD~1")
    changed_files = result.stdout.strip().splitlines()
    for file_path in changed_files:
        full_path = project_path / file_path
        if full_path.exists() and full_path.suffix in SUPPORTED_EXTENSIONS:
            index_file(project_id, full_path)
```

This ensures subsequent agents see completed work immediately after merge without requiring a full reindex.

---

## 7. Context Assembly Pipeline

### 7.1 Tiered Assembly Strategy

Context assembly follows a priority-ordered tier system from the product spec (F4). Higher tiers are always included; lower tiers are included up to the token budget:

| Tier | Content | Inclusion Rule |
|------|---------|----------------|
| 1 | Project spec, feature spec, task spec | Always verbatim — never truncated |
| 2 | Dependency artifacts (`blocked_by` at full content, `cross_refs` summarized) | Always included; summarized if budget is tight |
| 3 | Retry history (latest 2 full attempts, older ones summarized) | Included up to budget |
| 4 | RAG results (ranked by relevance) | Top 5 results, 500-char snippets |
| 5 | Chat history (current stage messages) | Most recent messages first, oldest dropped |

### 7.2 Current Implementation

The context builder (`pct.chat.context_builder`) assembles context for each chat turn:

```python
def resolve_task_context(session_id: str) -> tuple[str, str | None, str | None]:
    """Resolve cross-reference context for a task chat session.

    1. Parse session_id: "task-{featureId}-{taskId}"
    2. Load task frontmatter and body
    3. Collect referenced artifacts from:
       - Explicit cross_refs entries
       - [[wikilinks]] in task body
       - [[wikilinks]] in artifact content
    4. Expand stage prompt template with variables
    5. Return (cross_ref_context, artifact_type_hint, stage_prompt)
    """
```

The chat router then combines this with RAG results and conversation history before calling the agent:

```python
# In chat router send_message():
cross_ref_context, artifact_hint, stage_prompt = resolve_task_context(session_id)
rag_context = rag_search_context(project_id, user_message)

# Assemble system sections
system_parts = []
if cross_ref_context:
    system_parts.append(f"## Cross-References\n{cross_ref_context}")
if rag_context:
    system_parts.append(f"## World Knowledge (RAG)\n{rag_context}")
if artifact_hint:
    system_parts.append(f"## Artifact Type\n{artifact_hint}")
if stage_prompt:
    system_parts.append(f"## Stage Instructions\n{stage_prompt}")
```

### 7.3 Target Architecture

The target `ContextAssembler` class will centralize all assembly logic with token budgeting:

```python
class ContextAssembler:
    """Assembles agent context with token-aware budgeting."""

    def __init__(self, token_budget: int, context_manager: ContextManager | None = None):
        self.token_budget = token_budget
        self.context_manager = context_manager

    async def assemble(
        self,
        task: Task,
        feature: Feature,
        project_spec: str,
        chat_history: list[ChatMessage],
        rag_results: list[RAGResult],
    ) -> AssembledContext:
        # Tier 1: specs (always verbatim)
        base = f"{project_spec}\n\n{feature.spec}\n\n{task.spec}"
        remaining = self.token_budget - count_tokens(base)

        # Tier 2: dependency artifacts
        dep_context = self._resolve_dependencies(task)
        remaining -= count_tokens(dep_context)

        # Tier 3: retry history
        retry_context = self._build_retry_context(task, budget=remaining // 2)
        remaining -= count_tokens(retry_context)

        # Tier 4: RAG results
        rag_context = self._format_rag(rag_results, budget=remaining // 2)
        remaining -= count_tokens(rag_context)

        # Tier 5: chat history (most recent first)
        chat_context = self._trim_chat(chat_history, budget=remaining)

        # Optional: compress if over 75% of model context
        assembled = AssembledContext(
            base=base,
            retries=retry_context,
            rag=rag_context,
        )
        if self.context_manager and count_tokens(assembled.full_text) > self.token_budget * 0.75:
            assembled = await self.context_manager.prepare_context(assembled)

        return assembled
```

### 7.4 Context Manager Integration

The optional Context Manager (defined in Section 2, Tech Stack) is invoked when assembled context exceeds 75% of the target model's max context size. It uses a dedicated LLM agent to intelligently compress context — summarizing older retry attempts, ranking and trimming RAG results, and producing a coherent compressed context that preserves the most relevant information.

Configuration is in `pct.yaml`:
- `context_manager_agent_id` — which agent to use (typically a fast, cheap model like Claude Haiku)
- `context_manager_prompt` — the compression instruction prompt

When no Context Manager agent is configured, context is passed to the target model without compression (naive truncation as a last resort).

### 7.5 Template Variable Expansion

Stage prompt templates support variable substitution. The `_expand_stage_prompt()` function in the context builder resolves all variables:

**Built-in variables** (always available):

| Variable | Content |
|----------|---------|
| `{{artifact}}` | Full text content of the task's artifact |
| `{{artifact_work_dir}}` | Filesystem path to the task's work directory |
| `{{artifact_file_path}}` | Filesystem path to the feature document file |
| `{{task_title}}` | Task display name |
| `{{feature_title}}` | Feature display name |
| `{{blocked_by}}` | Concatenated artifact content from hard-blocking upstream tasks |
| `{{cross_refs}}` | Cross-reference context from soft-linked tasks |

**Custom variables** — user-defined key/value pairs from F10 Workflow Stages → Template Variables section. Keys are auto-slugified (e.g., `style_guide` → `{{style_guide}}`).

Expansion is simple string replacement — no Jinja2 or other template engines.

### 7.6 Token Counting

PCT uses different tokenizers depending on the target model:

| Target | Tokenizer | Notes |
|--------|-----------|-------|
| Local models (llama-cpp) | `llama_cpp` tokenizer | Exact count from the loaded model |
| Remote API (Claude, GPT) | `tiktoken` | Approximate; uses `cl100k_base` encoding |
| Fallback | `len(text) / 4` | Character-based estimate when no tokenizer is available |

Token counting is used for budget allocation in the `ContextAssembler`, not for precise billing.

### 7.7 Data Flow

```
┌─────────────┐
│ User message │
└──────┬──────┘
       ▼
┌──────────────────┐     ┌────────────────┐
│ resolve_task_     │────▶│ WikiLink       │
│ context()        │     │ resolution     │
│                  │     └────────────────┘
│ • cross_refs     │     ┌────────────────┐
│ • blocked_by     │────▶│ Artifact       │
│ • stage prompt   │     │ loading        │
│ • artifact hint  │     └────────────────┘
└──────┬──────────┘
       ▼
┌──────────────────┐     ┌────────────────┐
│ rag_search_      │────▶│ LanceDB        │
│ context()        │     │ vector search  │
└──────┬──────────┘     └────────────────┘
       ▼
┌──────────────────┐
│ AssembledContext  │
│ • base (specs)   │
│ • retries        │
│ • rag            │
│ • cross_refs     │
│ • stage prompt   │
└──────┬──────────┘
       ▼
┌──────────────────┐     ┌────────────────┐
│ Context Manager  │────▶│ Compression    │
│ (optional, >75%) │     │ LLM call       │
└──────┬──────────┘     └────────────────┘
       ▼
┌──────────────────┐
│ execute_chat_    │
│ turn()           │
│ • provider.exec  │
│ • tool loop      │
└──────┬──────────┘
       ▼
┌──────────────────┐
│ SSE stream       │
│ → frontend       │
└─────────────────┘
```

---

## Companion Documents

- **Product Specification** — see `docs/product_spec.md` (features F1–F13, user narrative, design principles)
- **Object Model** — see `docs/object_model.md` (§3 enumerations, §4 core entities, §5 agents & models, §6 workflow & configuration, §7 chat & context, §8 training pipeline, §9 image generation, §10 notifications, §11 relationships, §12 state machines)
