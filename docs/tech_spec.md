# PCT — Technical Specification v0.1 (Draft)

---

## 1. Storage Architecture

### Overview

PCT uses a **hybrid storage model** with three locations, each serving a distinct purpose:

1. **Project repo** (`.pct/`) — thin presence: specs, task definitions, lightweight kanban state
2. **PCT project state** (`~/.pct/projects/<project-id>/`) — heavy execution artifacts: agent logs, attempt history, RAG index, chat transcripts
3. **PCT global** (`~/.pct/curation/`) — cross-project reusable data: prompt templates, LoRAs, training examples, agent configs

### Design Principles

- **Specs are authoritative and live in the project repo.** The AI reads and writes specs and task definitions directly in `.pct/`. These are small, human-readable, and useful to keep with the project.
- **Execution artifacts live outside the project repo.** Agent logs, full attempt outputs, and RAG embeddings are large and machine-consumed. They don't belong in git.
- **No duplication.** Each piece of data has exactly one home. Specs and status live in the project repo. Execution details live in the external state. They reference each other by task ID, not by copying data.
- **PCT is the orchestrator.** AI agents don't need to know the directory structure. PCT assembles paths and context for each invocation.

### Directory Structure

#### Project Repo: `.pct/`

```
<project-root>/
  .pct/
    link.yaml                         # pointer to ~/.pct/projects/<project-id>/
    pct.yaml                          # project config: project ID, workflow stages,
                                      #   agent defaults, auto-advance rules,
                                      #   concurrency limits, context token budget
    project_spec.md                   # project-level specification
    active-features/                  # features with a defined spec and swimlane
      001-core-server/
        feature_spec.md               # feature-level specification
        metadata.yaml                 # machine-consumable: lifecycle stage, dependencies,
                                      #   swimlane info, worktree path, branch, commits
        tasks/
          001-define-data-models.md    # task definition + current status
          002-design-api-routes.md
          003-setup-scaffold.md
      002-frontend-kanban/
        feature_spec.md
        metadata.yaml
        tasks/
          001-design-component-tree.md
    feature_backlog/
      agent-execution-engine.md       # feature specs for backlogged features
      git-integration.md              #   (no tasks/ dir until activated)
```

**What lives here:**
- `link.yaml` — pointer to the external state directory for this project
- `pct.yaml` — project configuration: project ID, workflow stage definitions, default agent assignments, auto-advance rules, concurrency limits, context token budget
- `project_spec.md` — top-level project specification
- `active-features/<nnn>-<name>/feature_spec.md` — feature-level specifications
- `active-features/<nnn>-<name>/metadata.yaml` — feature lifecycle stage, cross-feature dependencies, swimlane state, worktree path, branch name, commit references
- `active-features/<nnn>-<name>/tasks/<nnn>-<slug>.md` — task definitions including: description, current status/stage, assigned agent, dependencies (intra- and cross-feature), tags, priority
- `feature_backlog/` — feature specs for features not yet started (no `metadata.yaml` or `tasks/` dir until activated)

Feature lifecycle state is encoded at two levels: the directory location (`active-features/` vs `feature_backlog/`) and the `metadata.yaml` lifecycle stage field (Planning, Active, Suspended, Integration Test, Complete).

**What does NOT live here:**
- Agent execution logs
- Full attempt outputs (rejected or approved)
- RAG embeddings
- Planning chat transcripts
- Anything large or machine-generated

**Size expectation:** A few KB per task, a few hundred KB total for a large project. Negligible git impact.

#### Task File Format

The full field specification for tasks is defined in the Object Model (§3, Task). The frontmatter is YAML; the body is human-readable Markdown. The AI reads and writes both. Attempt details are brief references — full outputs live in the execution state.

**Example task file:**

```markdown
---
id: "001"
title: "Define data models"
feature: "001-core-server"
status: "code-review"
agent: "claude-code"
branch: "feature/core-server/define-data-models"
depends_on: ["003"]
cross_depends_on:
  - "002-frontend-kanban/001"
tags: ["backend", "models"]
priority: 1
attempt: 3
created: "2026-02-12T10:00:00Z"
updated: "2026-02-12T14:30:00Z"
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

#### External State: `~/.pct/projects/<project-id>/`

```
~/.pct/
  projects/
    <project-id>/
      link.yaml                       # {"project_path": "~/projects/myapp"}
      execution/
        active-tasks/                 # tasks currently in progress
          001-define-data-models/
            attempt-001/
              agent_log.jsonl         # raw LLM messages (streaming transcript)
              output.md               # agent's produced output
              feedback.md             # rejection feedback (if rejected)
              metadata.yaml           # timestamp, agent, model, duration, tokens
            attempt-002/
              ...
            attempt-003/
              ...
        completed-tasks/              # archived after task reaches done
          001-design-component-tree/
            attempt-001/
              ...
        features/                     # feature-level execution artifacts
          001-core-server/
            integration-test/         # feature integration test attempts
              attempt-001/
                agent_log.jsonl
                output.md
                metadata.yaml
      chat_history/
        planning-001.jsonl            # initial project planning session
        planning-002.jsonl            # feature re-planning after swimlane suspend
      rag/
        tasks.lance/                  # LanceDB table: task execution embeddings
        specs.lance/                  # LanceDB table: spec/feature embeddings
      kanban_snapshots/               # periodic snapshots for timeline/history view
```

**What lives here:**
- `link.yaml` — maps this state dir back to the project path
- `execution/active-tasks/` — execution artifacts for in-progress tasks, each with attempt subdirectories
- `execution/completed-tasks/` — archived execution artifacts for finished tasks (moved from `active-tasks/` when task reaches done)
- `execution/features/` — feature-level execution artifacts, primarily integration test attempts that run when all tasks in a feature complete
- `chat_history/` — planning session transcripts (JSONL of messages)
- `rag/` — LanceDB tables (Lance columnar files) for vector search over task history and specs
- `kanban_snapshots/` — periodic captures of the full board state (for history/timeline features)

**Size expectation:** Can grow to many MB over the life of a project. No git overhead — this is never committed.

#### Global Curation: `~/.pct/curation/`

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
```

**What lives here:**
- Versioned prompt templates (reusable across projects)
- Curated training examples (positive and negative, from any project)
- Trained LoRA weights
- Agent configuration presets

### How AI Agents Interact with Storage

| Session Type | AI reads from | AI writes to |
|-------------|---------------|--------------|
| **Planning** | `.pct/` in project repo (specs, existing tasks) | `.pct/` in project repo (new/updated specs and task files) |
| **Implementation** | `.pct/` (task spec) + worktree (existing code) | Worktree (new code) |
| **Code Review** | `.pct/` (task spec) + worktree (diff/changes) | `.pct/` (review notes appended to task file) |
| **Refactoring Check** | `.pct/` (project spec) + project repo (merged code) | `.pct/` (new task files if opportunities found) |

PCT handles writing to the external execution state (`~/.pct/projects/`) — the AI doesn't touch it directly. PCT captures the agent's output stream and stores it after execution completes.

### Linking Project Repo to External State

`pct.yaml` in the project repo contains the project ID and all project-level configuration (see Object Model §3, ProjectConfig for the full schema):
```yaml
project_id: "a1b2c3d4"
project_name: "myapp"
project_type: "code"
project_directory: "C:/Users/gordo/projects/myapp"
workflow_stages:
  - stage: "refine-spec"
    label: "Refine Spec"
    enabled: true
    agent: null
    prompt_template: ""
  - stage: "implement"
    label: "Implement"
    enabled: true
    agent: "claude-code"
    prompt_template: "Implement the following task..."
  # ... additional stages
planning_agent: "claude-code"
default_agent: "claude-code"
auto_advance: true
concurrency:
  remote_api_limit: 2
  local_gpu_limit: 1
context:
  token_budget: 8000
  context_manager_model: "claude-haiku"
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

`~/.pct/projects/a1b2c3d4/link.yaml` maps back:
```yaml
project_path: "C:/Users/gordo/projects/myapp"
project_name: "myapp"
created: "2026-02-12T10:00:00Z"
```

PCT resolves the link on startup. If the project path has moved, PCT prompts the user to re-link.

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
  .pct/                         # PCT project state (specs, tasks, config)
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
- Config files (`pct.yaml`, `link.yaml`): plain YAML parsed by `PyYAML`
- Feature metadata (`metadata.yaml`): plain YAML parsed by `PyYAML`
- Agent configs (`~/.pct/curation/agent_configs/*.yaml`): plain YAML parsed by `PyYAML`

The only exception is **streaming logs** (`agent_log.jsonl`, `planning-*.jsonl`) which use JSONL (JSON Lines) — an append-only format suited for real-time log capture where each line is an independent record.

`python-frontmatter` depends on `PyYAML`, so both parsers come from a single dependency.

```python
import frontmatter
import yaml

# Task files: YAML frontmatter + Markdown body
post = frontmatter.load("001-define-data-models.md")
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
- **SQL WHERE filtering** — filter with familiar SQL syntax: `.where("feature = 'core-server' AND status = 'rejected'")`. No custom DSL to learn.
- **Lightweight** — ~50MB installed (Rust core + PyArrow). Lightest of the three finalists.
- **Embedding functions** — built-in support for sentence-transformers, OpenAI, and custom embedding functions. Auto-embeds on insert.
- Alternatives evaluated:
  - ChromaDB: most popular but RAM-bound (HNSW index must fit in memory), custom filter DSL, no Pydantic integration, no aggregation
  - txtai: most powerful queries (full SQL + hybrid search) but pulls in PyTorch + full HF stack (~2GB+), overkill dependency weight
  - FAISS: fastest raw search but no metadata filtering, no persistence, requires building everything yourself
  - Qdrant: requires separate server process — against local-first philosophy

**Schema:** See Object Model §6 (RAG Storage Models) and §7 (Image Generation Models) for the `TaskDocument` and `SpecDocument` LanceModel definitions.

**Usage example:**
```python
# Add
table.add([TaskDocument(task_id="001", feature="core-server", ...)])

# Query: find similar rejected tasks for this feature
results = (table.search(query_vector)
    .where("feature = 'core-server' AND outcome = 'rejected'")
    .limit(5)
    .to_pydantic(TaskDocument))
```

**Embedding model:** `all-MiniLM-L6-v2` via sentence-transformers (runs locally, fast, 384-dimensional output, good quality for retrieval). Can be swapped for API-based embeddings if preferred.

**Storage location:** `~/.pct/projects/<project-id>/rag/` — Lance files live alongside other execution state, never committed to the project repo.

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
- Session metadata persisted per task at `{artifact_path}/images/session.json` (where `artifact_path` is the task's directory, e.g. `work/{feature}/{task}/`)
- Images stored as PNG files in `{artifact_path}/images/`
- Text artifacts stored at `{artifact_path}/main.md`

**User/Manual agent:**
- PCT presents the task spec in the UI and waits
- User marks the task complete (or rejects/modifies)
- No subprocess — just a state transition

**Tool System:**
- Backend provides a tool registry with available tools: `bash`, `file_tools`, `read_tool`, `search_tool`, `todo_tool`
- Tools are provided to agents during execution via a global singleton registry
- Created lazily from the project root

**Agent abstraction interface:** See Object Model §8 (AgentProvider) for the protocol definition and implementation table. All providers implement the same `execute()` / `interrupt()` interface. PCT doesn't care which backend is executing — it assembles context, calls `execute()`, streams output, and stores results.

### Agent Concurrency Pool

PCT enforces configurable concurrency limits using Python's built-in `asyncio` primitives — no external library needed:

- **`asyncio.Semaphore`** — one per agent type (remote API, local GPU). Caps how many agents of each type can run simultaneously. Defaults: 2 remote, 1 local.
- **`asyncio.Queue`** — tasks ready for agent execution are enqueued. Worker coroutines pull from the queue, acquire the appropriate semaphore, and execute.
- **`asyncio.TaskGroup`** (Python 3.11+) — manages the worker coroutines with structured concurrency. Automatic cancellation propagation if a critical failure occurs.

```python
class AgentPool:
    def __init__(self, remote_limit: int = 2, local_limit: int = 1):
        self.queue: asyncio.Queue[AgentJob] = asyncio.Queue()
        self.semaphores = {
            "remote": asyncio.Semaphore(remote_limit),
            "local": asyncio.Semaphore(local_limit),
        }

    async def submit(self, job: AgentJob):
        await self.queue.put(job)

    async def _worker(self):
        while True:
            job = await self.queue.get()
            async with self.semaphores[job.agent_type]:
                await job.provider.execute(job.task, job.context, job.on_output)
            self.queue.task_done()

    async def run(self, num_workers: int = 4):
        async with asyncio.TaskGroup() as tg:
            for _ in range(num_workers):
                tg.create_task(self._worker())
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
loguru
pydantic-settings
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

## Companion Documents

- **Object Model** — see `docs/object_model.md` (core models, enums, state machines, relationships, storage mapping)

## Open Sections (to be fleshed out during iterative feature design)

- 3. API Design (server endpoints, WebSocket events)
- 4. Agent Abstraction Layer (detailed interface, providers)
- 5. RAG Pipeline (embedding strategy, indexing triggers, retrieval ranking)
- 6. Git Worktree Management (lifecycle, cleanup, conflict handling)
- 7. Context Assembly Pipeline (how agent prompts are built from all context layers)
