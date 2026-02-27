# PCT — Project Construction Tool
## Product Specification v0.1 (Draft)

---

## 1. Vision

PCT is a local-first project management tool that uses LLM agents to plan, execute, review, and iterate on project tasks. It replaces the traditional "human does everything" workflow with a hybrid model where configurable AI agents handle tasks across a Kanban board, with the user maintaining full transparency and control.

PCT is **not limited to software development**. It supports any project type that can be decomposed into features and tasks — from building an app, to writing a D&D campaign, to preparing a business slide deck.

---

## 2. Core Concepts

### Project
A single body of work. One PCT instance per project. A project has a top-level specification, a set of features, and shared context that all agents can access.

### Feature
A major deliverable within a project. Features are represented as **swimlanes** on the Kanban board. Each feature has its own specification and task breakdown.

Examples:
- Software: "Authentication system", "REST API", "Admin dashboard"
- D&D: An individual adventure within a campaign world
- Business: A section of a slide deck or business plan

### Feature Lifecycle
Features have their own lifecycle stages, separate from the task workflow stages:

| Feature Stage | Description |
|--------------|-------------|
| **Backlog** | Feature spec exists but no task breakdown yet. Not visible on the Kanban board. |
| **Planning** | Feature is being decomposed into tasks via the planning chat. The planning agent proposes a task breakdown and dependency graph; the user reviews and edits specs at any level (project, feature, task). Feature moves to Active only when the user approves the spec and task breakdown. |
| **Active** | Tasks are flowing through the Kanban workflow. The swimlane header shows progress (e.g., `[Active — 4/7 tasks complete]`). |
| **Suspended** | All agents halted, in-flight state preserved. Planning chat reopens scoped to this feature for re-specification. On resume, impact analysis identifies affected tasks. (See F8.) |
| **Integration Test** | All tasks in the feature have completed the task workflow. A feature-level agent run verifies that all merged task outputs work together. If integration testing fails, new tasks are spawned back at Refine Spec. |
| **Complete** | Feature has passed integration testing. Swimlane moves to the completed archive. |

The feature lifecycle governs **when decomposition and re-planning happen**: specs are created and edited during the Planning and Suspended stages. Mid-flight spec changes require suspending the feature first.

### Task
A single unit of work within a feature. Tasks flow through the Kanban workflow stages. Each task is assigned to an **agent** (LLM or user) and executes within a specific context assembled from the project spec, feature spec, RAG history, and prior attempts.

Tasks support **explicit dependencies** — both within a feature and across features. The planning agent proposes an initial dependency graph during task decomposition; the user can review and edit it. Tasks with unmet dependencies remain blocked in their current column. Cross-feature dependencies are modeled as task-level blocks across swimlanes (e.g., "Task X in Feature B is blocked by Task Y in Feature A").

Tasks can be added mid-flight to an active swimlane — by the user manually, or by agents (e.g., the refactoring-check agent or integration test failures spawning new tasks). New tasks always enter at the Refine Spec workflow stage.

### Agent
A standalone, named configuration that defines an executor. An agent can be:
- **LLM Agent** — an AI model (local or remote) with a configured prompt template, model, and optional LoRA
- **User Agent** — the human does the work manually
- **Tool Agent** — a custom tool or script (future)
- **Image Generation Agent** — a diffusion model (HuggingFace Diffusers) that generates images from text prompts. When selected in the chat input, prompts are routed to the image generation pipeline instead of the chat pipeline.

Agents are **defined in the Project Configuration page (F10)** by combining a model (from the Model Registry), an optional LoRA adapter (from the LoRA Registry), a prompt template, and provider-specific settings. Once defined, an agent is a reusable, named entity available throughout the project — workflow stages, features, tasks, and the planning chat all reference agents by ID.

The agent assigned to a task is configurable **per workflow stage, per feature, and per task**. A task might use Claude Code for implementation but a local LLM for code review.

### Model Registry
A global catalog of available models — local (e.g., Llama 3 weights on disk), remote (e.g., Claude Sonnet via API), and HuggingFace Hub (downloaded on demand). Each entry records the model identifier, provider type, context length, and provider-specific details (file path for local/HuggingFace, API endpoint for remote). The registry also tracks **download status** for HuggingFace models (pending → downloading → ready → error). The registry provides **dropdown population** in the agent configuration UI. Models are registered once and shared across all projects. PCT can also **auto-discover** local models by scanning project and global model directories for `.gguf` and `.safetensors` files.

### LoRA Registry
A global catalog of available LoRA adapters. Each entry records the adapter name, compatible base model, file path, and description. LoRA entries reference a Model Registry entry to enforce compatibility — the agent configuration UI only shows LoRAs compatible with the selected base model. Like the Model Registry, this is global and provides **dropdown population** in the agent configuration UI.

### Workflow Stage (Kanban Column)
The stages a task passes through. The Kanban columns **are** the workflow stages:

| Stage | Description | Typical Agent |
|-------|-------------|---------------|
| **Refine Spec** | Clarify requirements, produce a task-level specification | LLM or User |
| **Implement** | Execute the work (write code, create content, etc.) | LLM or User |
| **Feature Test** | Run tests scoped to this task/feature | Automated / LLM |
| **Code Review** | Another agent reviews the work for quality and correctness | LLM (different from implementer) |
| **User Approval** | Human reviews and approves or rejects | User (always) |
| **Merge** | Merge the task branch into the development branch | Automated |
| **Full Test Suite** | Run the complete project test suite post-merge | Automated |
| **Refactoring Check** | Agent scans for refactoring opportunities, may spawn new tasks | LLM |
| **Push** | Push to remote | User-confirmed (always) |

Not all stages apply to every project type. PCT provides **workflow templates** per project type with sensible defaults for which stages are active and what agents do at each stage. Workflow stages are configurable per project via the Project Configuration page (F10).

Each stage maintains its own **per-stage context window** — the chat history between the user/agent at that stage is stored independently. When a task advances, the context window clears for the new stage; when a task is sent back, the previous stage's context is restored. See "Stage transition behavior" in the Chat Interface section for details.

### Context
The assembled information an agent receives when executing a task. Context is built from multiple layers:

1. **Project specification** — top-level goals, conventions, constraints
2. **Feature specification** — the feature this task belongs to
3. **Task specification** — what this specific task should accomplish
4. **RAG-injected history** — relevant prior task results, rejected attempts, related work from other features
5. **Retry history** — all prior attempts at this task, including rejections and user feedback

RAG context injection happens at **every workflow stage**, not as an optional feature but as a core part of the agent invocation pipeline.

### Feedback Loop
When a task output is rejected (by a review agent or by the user):
1. The rejected output and feedback are stored as a **negative example**
2. The task is re-run with the full retry history: all prior attempts + all rejection feedback
3. For recurring issues, users curate **prompt templates** — versioned agent instructions that evolve over time
4. For model-level improvement, positive and negative examples are collected for **LoRA fine-tuning**, managed and executed by PCT

---

## 3. Features

### Chat Interface (shared foundation)
The Chat Interface is the unified interaction model shared by both the Planning Window (F1) and the Task Detail Panel (F3). Both present the same three-section layout: a scrollable context/message window, a compact input section, and an artifact/output section. The only differences are what context is scoped to (project-level vs. task-level) and what additional chrome surrounds the chat.

**Section 1 — Context Window** (top, scrollable):
- Chat message history with the active agent
- Agent output stream (real-time when running)
- **Message curation controls** — each message bubble exposes:
  - **Include/Exclude checkbox** — toggles whether the message is included in the context sent to the agent on subsequent prompts
  - **Edit button** — opens inline editing mode where the user can modify message content and change the message role (user/assistant/system)
  - **Delete button** — removes the message from the session
  - **Copy-to-artifact button** (assistant messages only) — appends the assistant's response to the current artifact file on disk
  - **Replay button** (user messages only) — resends the user message to the agent
  - **Truncate & stage button** (user messages only) — deletes this message and all subsequent messages, then populates the input field with the message text without automatically sending it. The user can review, edit, or resend at their discretion.
- **Streaming** — agent responses stream token-by-token via Server-Sent Events (SSE), with a visual streaming indicator
- **Context inspector toggle** — a toggle button in the context window header switches between two views:
  - **Chat view** (default) — the standard message history described above
  - **Inspector view** — displays the full assembled context that will be sent to the agent on the next prompt. Shows each context section (project spec, feature spec, task spec, RAG results, retry history) as collapsible panels with token counts per section and a total token count. The user can edit, add, remove, or reorder any section before sending. Essential for working with local models that have restricted context windows. Changes made in the inspector are reflected in the next agent invocation without altering the source specs.

**Section 2 — Input** (middle, compact):
- **Agent selector dropdown** — user can change the agent (and therefore model) between prompts. The dropdown shows configured agents with the default agent indicated by an asterisk. Default agent resolution follows a waterfall: workflow stage agent → project `default_agent` → `planning_agent` → first available agent.
- Text input with send/stop controls
- **Refine chip** — when an image is selected for refinement, shows a thumbnail + "Refining [image]" banner with cancel option. Auto-switches agent to imagegen.
- **Image generation routing** — when an image generation agent is selected, prompts are routed to the image generation pipeline instead of the chat API

**Section 3 — Artifact / Output** (bottom, split view):
- **Text sub-section**: Rendered markdown preview of the active text artifact. Edit button opens a rich text modal (TipTap). File path, reload, save controls. WikilinkStrip tag display. Collapsible. Artifacts are directory-based — each artifact path points to a directory containing `main.md` for text and `images/` for generated images.
- **Image sub-section**: Thumbnail grid of all generated images. Each image has hover actions: "Refine" (sends to input section) and "View" (opens full-size gallery modal). When imagegen agent is active, shows generation params (negative prompt, divergence, guidance). Progress bar during generation. Round history. Collapsible.
- **Image Gallery Modal**: Full-screen viewer (80vw × 80vh) for generated images. Left/right navigation. Image metadata (seed, round, index). Refine and Accept action buttons.

**Cross-section communication** (identical in all contexts):
- Context → Artifact: "Copy to artifact" appends chat responses to text file
- Artifact → Input: "Refine" on image pre-fills input and switches to imagegen agent
- Input → Artifact: Sending prompts generates content in the active artifact type

**Stage transition behavior** (applies to Task Detail Panel context windows):
- **Per-stage context storage** — the context window (chat history) is stored separately for each workflow stage. Each stage maintains its own conversation history with its own agent.
- **Advance on approval** — when work at a stage is approved, the task card automatically advances to the next workflow stage. Whether the next stage's agent auto-runs is controlled by the `auto_advance` toggle (F10 General tab). Advancing state and auto-running the agent are independent: the card always moves, but agent execution can wait for user initiation.
- **Clear on advance** — when a task advances to a new stage, the context window resets to a fresh state. The new stage's agent receives a clean assembled context (project spec, feature spec, task spec, artifact, RAG-selected history) without the previous stage's conversational back-and-forth. The artifact is the handoff mechanism between stages.
- **Restore on return** — if a task is dragged back to a previous stage (e.g., from Code Review back to Implement), the context window for that stage is restored in full. All messages from the previous time the task was at that stage reappear exactly as they were. This makes stage transitions non-destructive — moving forward clears the view, moving backward restores it.
- **Carry-forward override** — optional toggle on the approval action for rare cases where the user wants the next stage's agent to see the current stage's raw conversation in addition to the assembled context.

---

### F1: Planning Window
The entry point for every project. A **Chat Interface** (see above) where the user collaborates with a planning agent to define:
- Project scope and specification
- Feature breakdown
- Initial task decomposition

The Planning Window is also used when:
- A new feature is being specified
- A swimlane is suspended for re-planning (scoped to that feature)
- The user wants to revise the project or feature spec mid-flight

The planning conversation becomes part of the project's permanent context. There is no Kanban board until planning produces features and tasks. Once the Kanban board appears, the Planning Window persists as a sidebar.

**Main artifact — `work/INDEX.md`:**
The Planning Window's artifact section displays the **project index** — an auto-generated markdown file that serves as the master reference for all work in the project. The index contains:
- **Project overview** — top-level project spec reference
- **Feature catalog** — a header for each feature with links to feature specs
- **Task index** — organized by feature, with links to all task artifacts
- **Work products catalog** — paths to all generated artifacts (text, images)
- **Cross-references** — WikiLink support for inter-artifact connections

The index is auto-regenerated after task completion, on "Re-index work artifacts" (F10 General tab), and on project sync/refresh. This makes the Planning Window the central navigation hub — it shows the full project landscape just as a task pane shows a single task's output.

Image generation and artifact editing work identically to the task pane: when an imagegen agent is selected, images are generated into the project-level artifact directory; the text artifact (INDEX.md) can be edited via TipTap; the "Copy to artifact" action appends to the index.

### F2: Kanban Board with Swimlanes
The primary project view once planning is complete. Displays:
- **Swimlanes** (rows) — one per active feature
- **Columns** — workflow stages
- **Task cards** — showing title, assigned agent, feature tag, status indicators

Capabilities:
- Real-time updates as agents complete work
- **Drag-and-drop** for manual task movement with **stage skip confirmation** — moving a task to a non-adjacent stage shows a confirmation modal listing the skipped stages
- **Cross-feature task reassignment** — dragging a task to a different swimlane reassigns it to that feature
- Swimlane controls: activate, suspend, resume
- **Swimlane collapse/expand** — each swimlane can be collapsed to save space, with state persisted across navigation
- **Cross-swimlane dependency indicators** — visual links showing when a task in one feature is blocked by a task in another feature
- **Backlog view** with **activate buttons** for promoting features to active status
- Completed archive for finished tasks
- **Filtering** — multi-select feature filter, toggles for suspended/complete feature visibility
- **Inline task creation** — add tasks directly from the swimlane header, with artifact type inferred from existing tasks in the feature
- **Task card visual indicators:**
  - Left border color indicates agent type (LLM: blue, User: green, Tool: gold)
  - **Artifact type color dot** — small colored indicator showing the task's artifact type
  - Blocked tasks shown with reduced opacity
  - Selected/dragging tasks highlighted with blue background
- **Swimlane header controls:**
  - Feature title and lifecycle stage badge (color-coded)
  - Progress indicator (completed tasks / total tasks)
  - Add Task button
  - **Analyze dropdown** — triggers Gap Analysis or Continuity Check (see below)
  - Suspend/Resume toggle
- **Feature Analysis Tools** (accessible from swimlane header):
  - **Gap Analysis** — an LLM-powered analysis that identifies missing tasks within a feature, streamed via SSE. Results include suggested tasks with title, feature, artifact type, and reasoning. Each suggestion has a one-click "Create" button.
  - **Continuity Check** — verifies narrative/specification consistency within a feature, also streamed via SSE with the same suggestion format.

### F3: Task Detail Panel
Resizable slide-out panel (min 500px, max 900px, default 520px, draggable via left-edge handle) when clicking a task card. Contains a full **Chat Interface** (see above) plus a task-specific header. The three-section layout (context window, input, artifact/output) is identical to the shared Chat Interface — the only difference is that context and artifacts are scoped to a single task.

**Header section** (above the Chat Interface):
- Task title
- **Artifact type selector** — dropdown to assign/change the task's artifact type (e.g., chapter, character, timeline, code). Artifact types are configurable per project (see F10).
- Feature and task ID display
- **Cross-references section** — tag strip showing `cross_depends_on` references with:
  - "Add Ref" button opening a **CrossRefPicker modal** — a feature-grouped checklist of all tasks in the project for selecting cross-dependencies
  - Closable tags for removing references
  - Hint about `[[wikilink]]` auto-linking in artifacts

**Task-specific artifact scoping:**
- The artifact directory is `work/{feature_id}/{task_id}/`, containing `main.md` for text and `images/` for generated images. Legacy single-file `.md` paths are still supported.
- The agent selector defaults per workflow stage but is overridable per task.

**Stage controls:**
- **Agent configuration** for the current stage (prompt template, model, LoRA)
- **Full execution history** — all attempts with diffs between versions
- **Raw message inspector** — view the actual LLM messages (system prompt, user messages, assistant responses) for full transparency
- Controls: Run Agent, Approve, Reject (with feedback), Reassign Agent, Interrupt, Send Back to Stage

### F4: Agent Execution Engine
Manages the lifecycle of agent task execution:
- **Context assembly** using a tiered strategy: (1) always include project spec, feature spec, and task spec; (2) include latest 2 full retry attempts, summarize older ones; (3) RAG results ranked by relevance, included up to a configurable token budget. The context inspector toggle in Section 1 of the Chat Interface allows the user to view and modify the assembled context before execution.
- **Context Manager** — an LLM-powered tool that intelligently summarizes, compresses, and prioritizes context to fit within model token limits. The Agent Execution Engine calls the Context Manager automatically before each agent invocation. The Context Manager is also exposed as a tool/skill that agents can invoke directly during execution (e.g., to request additional context or re-summarize mid-task). The Context Manager uses a configurable model — remote models are guided via prompt skills, local models can be fine-tuned with LoRA for project-specific summarization quality. This is a core PCT differentiator: intelligent context management rather than naive truncation.
- Invokes the configured agent (LLM call, CLI command, or user prompt)
- Streams output in real-time to the task detail panel
- Supports **interruption** — user can stop an agent mid-execution
- Handles parallel execution — multiple agents across different tasks/swimlanes simultaneously, subject to concurrency limits configured in F10
- Each agent execution happens in an isolated environment (git worktree)

Agent abstraction layer supports:
- **Remote API** — Claude Code CLI (primary), with room for other providers
- **Local LLM** — via llama-cpp-python or similar
- **HuggingFace** — models downloaded from HuggingFace Hub, run locally
- **User** — PCT presents the task to the user and waits for manual completion
- Common interface regardless of backend

### F5: Git Integration
Git is universal — **all project types** use git, not just code projects. Non-code projects produce text-mergeable documents (LaTeX, RTF, Markdown) that flow through the same pipeline:
- **Branch-per-task**: each task gets a branch (e.g., `feature/core-server/define-data-models`)
- **Worktree-per-task**: agents work in isolated worktrees, not the main working directory
- **Merge stage**: automated merge attempt with conflict detection
- **User escalation on merge failure**: PCT flags the conflict on the task card, notifies the user, and waits for the user to resolve using their own editor and merge tools (VS Code, vim, meld, etc.). No built-in diff/merge UI — the user signals PCT when resolution is complete.
- Worktree cleanup after successful merge and push

### F6: RAG & Task History
Local storage with retrieval-augmented generation for surfacing relevant context:
- **What gets stored**: every task execution (input context, agent output, approval/rejection, user feedback), project and feature specs, planning chat history
- **What gets retrieved**: similar past tasks, rejected approaches (especially valuable), related work from other features, previously created artifacts (code functions, story characters, design decisions)
- **When it's used**: every agent invocation — RAG results are injected into the context assembly pipeline
- **User querying**: search and browse task history, filter by outcome, feature, agent, stage

### F7: Feedback & Training UI
Dedicated interface for improving agent quality over time:
- **Example browser**: view all positive and negative task executions
- **Prompt template editor**: versioned agent prompt templates, editable per task type and workflow stage
- **Training data curation**: select and annotate examples for LoRA fine-tuning
- **Training execution**: PCT kicks off LoRA training runs using curated data
- **A/B comparison**: view before/after when a prompt template or LoRA is updated

### F8: Swimlane Management
Controls for parallel workstream management:
- **Activate**: start a feature from the backlog, create initial tasks
- **Suspend**: immediately halt all running agents on the swimlane, preserve in-flight task state, open the planning chat scoped to this feature for re-specification
- **Resume**: restart suspended tasks (optionally clearing state and restarting from an earlier stage)
- **Clear & Restart**: invalidate all in-flight tasks on a swimlane and restart them from Refine Spec with updated context
- **Impact analysis on resume**: PCT identifies which tasks may be affected by spec changes during suspension

### F9: Session & Project Management
- Project creation and configuration
- Session persistence — close and reopen PCT without losing state
- Export/import project state

### F10: Project Configuration Page
Dedicated settings page with **six tabs** for managing project-level configuration:

**General tab:**
- **UI Preferences** — font size slider (10–20px), persisted to localStorage
- **Project metadata** — project name, project type (Coding / Writing), project directory (read-only)
- **Re-index work artifacts** — button to scan the work directory and rebuild the RAG index
- **Planning & defaults** — planning agent selector, default agent selector (fallback for ChatInput when no stage agent is configured), auto-advance toggle
- **Agent concurrency limits** — max parallel remote API agents (default: 2), max parallel local GPU agents (default: 1). Excess tasks queue until a slot opens.

**Model Registry tab:**
- View, add, edit, and remove entries in the global Model Registry. Each entry specifies a model name, **provider type** (Remote API / Local LLM / **HuggingFace**), model identifier, context length, and provider-specific details (model file path for local/HuggingFace, API base URL for remote). For local and HuggingFace models, a **file browser** button opens a filesystem navigation modal for selecting model paths. Context length tooltip explains that 0 = use model default. The registry is global (shared across projects) and populates model dropdowns throughout the agent configuration UI.

**LoRA Registry tab:**
- View, add, edit, and remove entries in the global LoRA Registry. Each entry specifies an adapter name, the compatible base model (selected from the Model Registry), file path to weights, and a description. The UI enforces base-model compatibility — only LoRAs matching the selected model appear in dropdowns.

**Agents tab:**
- Define named agents for this project. Each agent combines: a model (dropdown from Model Registry), an optional LoRA (dropdown from LoRA Registry, filtered by selected model), an **agent type** (LLM / User / Tool / **Image Gen**), a **provider type** (Remote API / Local LLM / **HuggingFace** / User), a prompt template, and provider-specific settings (CLI command for remote, temperature and context length overrides). Agents are standalone entities identified by ID and referenced elsewhere in the project. The configuration UI supports creating, editing, and deleting agents.

**Workflow Stages tab:**
- **Drag-and-drop reorderable** stage list. Each stage has:
  - **Name** — display label (auto-generates a slugified ID unless manually changed)
  - **Prompt template** — optional per-stage prompt template injected into agent context
  - **Enabled toggle** — whether this stage is active for the project
  - **Agent selector** — default executor for tasks entering this stage (overridable per task)
  - Inline save/cancel controls for dirty edits; delete for unused stages
  - "Add Stage" button to create new custom stages
- **Template Variables** (collapsible section):
  - **Built-in variables** (read-only reference): `{{artifact}}` (full artifact content), `{{artifact_path}}` (file path), `{{task_title}}`, `{{feature_title}}`, `{{cross_refs}}` (cross-reference context)
  - **Custom variables** — user-defined key/description/value triples that are substituted into stage prompt templates. Keys are auto-slugified (lowercase alphanumeric).

**Artifact Types tab:**
- Define custom artifact types for task categorization. Each type has:
  - **Label** — display name (auto-generates a slugified ID)
  - **Template hint** — instructional text injected into the agent's system prompt when working on tasks of this type
- Built-in defaults include: timeline, location, character, faction, magic-system, technology, item, story-arc, chapter, text
- Artifact types appear as a **color-coded dot** on task cards and as a dropdown selector in the task detail panel header

All project-level settings persist to `pct.yaml` in the project repo. The Model Registry and LoRA Registry persist globally to `~/.pct/registries/`.

**Feature serialization** — per-feature toggle for serial vs. parallel task execution. Features producing non-mergeable artifacts (images, video, binary formats) must use serial execution since outputs cannot be git-merged.

### F11: Image Generation
Integrated image generation for visual content creation within tasks. Image generation is triggered by selecting an image generation agent in the chat input — prompts are routed to the image generation pipeline instead of the chat API.

**Image Generation Pane** (replaces the artifact pane when an imagegen agent is active):
- **Negative prompt** — collapsible section for specifying what to exclude from generation
- **Parameters:**
  - **Divergence slider** (0.1–0.9, labeled Close / Balanced / Diverge) — controls img2img variation strength. Only shown when a prior generation round exists (i.e., there is a source image for img2img refinement).
  - **Guidance scale** — numeric input (default: 7.5) controlling how closely the model follows the prompt
- **Generation output** — 2×2 image grid showing the 4 images from the latest round. Click to select an image; selected image is highlighted with a border.
- **"Accept Selected Image"** button — saves the selected image as the task's artifact
- **Round history** — collapsible section showing previous generation rounds, each with the prompt used and a thumbnail grid. Selected images are marked in history.
- **Progress bar** displayed during generation

**Backend:**
- Uses HuggingFace Diffusers (default model: `sd-legacy/stable-diffusion-v1-5`)
- Supports both **text-to-image** (first round) and **image-to-image** (subsequent rounds using the selected image as source)
- Generates 4 images per round with configurable parameters: prompt, negative_prompt, guidance_scale, num_inference_steps, width, height, seed, divergence
- Asynchronous job-based execution with polling for status and progress
- Image session metadata persisted per task at `work/{feature_id}/{task_id}/images/session.json`

---

## 4. User Narrative: Building PCT with PCT

### Act 1: Project Kickoff — The Planning Chat

The user launches PCT. The screen shows a **chat interface** — no Kanban board yet.

> **User:** I want to build a Project Construction Tool. It's a Python/React app that uses LLM agents to execute project tasks on a Kanban board. Here's my rough idea...

The **planning agent** (Claude Code) engages in back-and-forth, asking about deployment model, workflow stages, project types, and agent execution. The conversation is persistent — it becomes the project's base context.

After several exchanges, the planning agent proposes a project specification and feature breakdown:

> **Planning Agent:** I propose breaking this into the following features:
> 1. Core Server & API
> 2. React Frontend — Kanban
> 3. Planning Chat UI
> 4. Agent Execution Engine
> 5. Git Integration
> 6. RAG & Storage
> 7. Feedback & Training UI
>
> Shall I create the Kanban with these as swimlanes?

> **User:** Yes, but start with features 1-3 as active. Keep 4-7 in the backlog.

### Act 2: The Kanban Appears

The chat slides to a sidebar and the Kanban board materializes:

```
SWIMLANE: Core Server & API                                         [Active]
 Refine Spec        | Implement | Test | Review | Approval | Merge | Push
 [Define data models]
 [Design API routes]
 [Setup scaffold]

SWIMLANE: React Frontend — Kanban                                   [Active]
 [Design component tree]

SWIMLANE: Planning Chat UI                                          [Active]
 [Define chat protocol]

BACKLOG: Agent Execution Engine, Git Integration, RAG & Storage, Feedback UI
```

Each task card shows its title, assigned agent, and feature tag.

### Act 3: First Agent Run — Spec Refinement

The user clicks **"Define data models"**. The task detail panel slides out showing:
- **Stage:** Refine Spec
- **Agent:** Claude Code (auto)
- **Prompt template:** "Given the project spec and feature spec for {feature}, define the data models for: {task_description}"
- **Context:** Project spec + Feature spec for "Core Server & API"

The user clicks **"Run Agent"**. PCT creates a git branch and worktree, then invokes Claude Code. The user watches the agent's raw messages stream in real-time.

The agent produces a spec proposing SQLAlchemy ORM models. The user opens the raw message inspector, sees the full conversation, and clicks **Reject**:

> **User feedback:** "Don't use SQLAlchemy. We're doing local file storage. Rethink as Pydantic models persisted to JSON files."

PCT stores the rejection, re-runs the agent with the original context plus the full rejection history. The agent revises. User approves. Card advances to **Implement**.

### Act 4: Parallel Work

Three tasks are now ready for implementation:

```
 Implement
 [Data models] .......  Agent: Claude Code (running)
 [Scaffold] ..........  Agent: User (manual)
 [Component tree] ....  Agent: Claude Code (running)
```

Two LLM agents run in parallel in separate worktrees. The user works on the scaffold manually. The Kanban updates in real-time — spinning indicators on agent tasks, a user icon on the manual task.

The user clicks into the running "Data models" task and watches the raw LLM conversation. They notice the agent heading in a wrong direction and click **Interrupt**. The agent stops. The user adds guidance and re-runs.

### Act 5: Code Review — Agent Reviews Agent

"Data models" implementation completes and auto-advances through Feature Test (pytest passes) to **Code Review**.

The review stage uses a **different agent and prompt** — configured to check correctness, adherence to project conventions, and spec compliance. The reviewing agent flags:

> "The Task model is missing a `status_history` field mentioned in the spec."

The task stays in Code Review. The user sees the review, agrees, and sends the task **back to Implement** with the review feedback attached. The implementing agent receives the full history (original spec, first implementation, review feedback) and produces a corrected version.

The corrected version passes review. The task advances to **User Approval**.

### Act 6: Swimlane Suspension

While tasks are flowing, the user realizes the API design needs WebSockets instead of REST polling.

> **User clicks "Suspend" on "Core Server & API".**

PCT immediately:
1. Halts all running agents on the swimlane
2. Preserves in-flight task state
3. Grays out the swimlane
4. Opens the planning chat scoped to this feature

The user revises the feature spec with the planning agent. When done, PCT runs impact analysis:

> **PCT:** These tasks may be affected by the spec change:
> - "Design API routes" — directly contradicted
> - "Setup scaffold" — may need WebSocket dependencies
>
> Clear and restart? [Yes / Selective / No]

The user selects "Yes." Affected tasks reset to Refine Spec with updated context. Swimlane resumes.

### Act 7: Merge, Test, Push

"Design component tree" (Frontend) completes all stages and reaches **Merge**:

1. PCT runs `git merge feature/frontend/component-tree` into the development branch
2. No conflicts — merge succeeds
3. **Full Test Suite** runs — all tests pass
4. **Refactoring Check** — an agent scans the merged code, finds no issues (or spawns new tasks if it does)
5. Card reaches **Push** — PCT prompts the user for confirmation

> **User clicks Push.**

The branch is pushed. The card moves to the completed archive.

### Act 8: RAG in Action

Later, the "Agent Execution Engine" feature is activated from the backlog. A task for "implement agent abstraction layer" enters Refine Spec.

PCT's RAG automatically injects into the agent's context:

> *Related prior work: The data model task went through 2 iterations. The first was rejected for using SQLAlchemy — the approved approach uses Pydantic models with JSON persistence. Relevant models: [excerpts]. The API was revised mid-project to use WebSockets — see updated feature spec.*

The agent starts with the right assumptions because it learned from the project's history — including the mistakes.

### Act 9: Prompt Curation

After several features, the user notices agents keep proposing overly complex solutions. They open the **Feedback & Training UI**, browse negative examples, and spot the pattern. They edit the base prompt template:

> *Added to project-level agent instructions: "Prefer simple, minimal implementations. Avoid ORMs, complex abstractions, and over-engineering. Use Pydantic models with JSON file persistence unless explicitly directed otherwise."*

All future agent invocations inherit this updated instruction. The user also selects 5 rejected examples and 5 approved examples and kicks off a LoRA fine-tuning run to bake this preference into the local model.

---

## 5. UI States Summary

| State | Interface |
|-------|-----------|
| Project kickoff | Planning Window (full Chat Interface with INDEX.md artifact) — no Kanban |
| First launch (uninitialized) | Redirects to Settings page for initial project configuration |
| Planning complete | Planning Window sidebar + Kanban board (main view) |
| Task detail | Resizable slide-out Task Detail Panel (full Chat Interface scoped to task, plus header with artifact type, cross-refs) |
| Agent running | Live SSE streaming + streaming indicator + stop button (same in both Planning Window and Task Detail) |
| Feature analysis | Modal with streaming analysis output, suggested tasks with create buttons |
| Swimlane suspended | Grayed swimlane + Planning Window opens scoped to feature |
| Feature integration test | Swimlane header shows integration test status; agent output streams in feature-scoped panel |
| Feedback/training | Dedicated view: example browser, prompt editor, training controls |
| Project configuration | Settings page with 6 tabs: General, Model Registry, LoRA Registry, Agents, Workflow Stages, Artifact Types |

---

## 6. Design Principles

1. **Extreme transparency** — The user can always see exactly what an agent is doing, including raw LLM messages. No black boxes.
2. **User control** — Every automated action can be interrupted, overridden, or reassigned to a human. The user is always the final authority.
3. **Context continuity** — Project knowledge accumulates and is shared. Agents learn from the project's history, including mistakes.
4. **Project-type agnostic** — The core workflow (plan, decompose, execute, review, iterate) works for code, content, and creative projects alike.
5. **Local-first** — Runs on the user's machine. No cloud dependency required (though remote LLM APIs are supported).
6. **Configurable workflow** — Stages, agents, auto-advance rules, and approval gates are all configurable per project, feature, and task type.
