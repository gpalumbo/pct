# PCT — Project Construction Tool
## Product Specification v0.1 (Draft)

---

## Table of Contents

1. [Vision](#1-vision)
2. [Core Concepts](#2-core-concepts)
   - [Project](#project)
   - [Feature](#feature)
   - [Feature Lifecycle](#feature-lifecycle)
   - [Task](#task)
   - [Agent](#agent)
   - [Model Registry](#model-registry)
   - [LoRA Registry](#lora-registry)
   - [Workflow Stage (Kanban Column)](#workflow-stage-kanban-column)
   - [Context](#context)
   - [Feedback Loop](#feedback-loop)
3. [Features](#3-features)
   - [Chat Interface (shared foundation)](#chat-interface-shared-foundation)
   - [Artifact Strategy (shared foundation)](#artifact-strategy-shared-foundation)
   - [F1: Planning Window](#f1-planning-window)
   - [F2: Kanban Board with Swimlanes](#f2-kanban-board-with-swimlanes)
   - [F3: Task Detail Panel](#f3-task-detail-panel)
   - [F4: Agent Execution Engine](#f4-agent-execution-engine)
   - [F5: Git Integration](#f5-git-integration)
   - [F6: RAG & Task History](#f6-rag--task-history)
   - [F7: Feedback & Training UI](#f7-feedback--training-ui)
     - [Phase 1: Data Collection](#phase-1-data-collection-in-chat-interface)
     - [Phase 2: Training Data Browser & Curation](#phase-2-training-data-browser--curation-f7-training-data-tab)
     - [Phase 3: Dataset Builder & Training Kickoff](#phase-3-dataset-builder--training-kickoff)
     - [Phase 4: Post-Training — Evaluation & Agent Integration](#phase-4-post-training--evaluation--agent-integration)
   - [F8: Swimlane Management](#f8-swimlane-management)
   - [F9: Session & Project Management](#f9-session--project-management)
   - [F10: Project Configuration Page](#f10-project-configuration-page)
   - [F11: Image Generation](#f11-image-generation)
   - [F12: PERT Chart](#f12-pert-chart)
   - [F13: Notifications](#f13-notifications)
4. [User Narrative: Building PCT with PCT](#4-user-narrative-building-pct-with-pct)
   - [Act 1: Project Kickoff](#act-1-project-kickoff)
   - [Act 2: The Kanban Appears](#act-2-the-kanban-appears)
   - [Act 3: Refine Feature — Task Decomposition](#act-3-refine-feature--task-decomposition)
   - [Act 4: First Agent Run — Spec Refinement](#act-4-first-agent-run--spec-refinement)
   - [Act 5: Parallel Execution](#act-5-parallel-execution)
   - [Act 6: Code Review — Agent Reviews Agent](#act-6-code-review--agent-reviews-agent)
   - [Act 7: Spec Change & Impact Analysis](#act-7-spec-change--impact-analysis)
   - [Act 8: Merge Through Push](#act-8-merge-through-push)
   - [Act 9: RAG in Action](#act-9-rag-in-action)
   - [Act 10: Prompt Curation & Training](#act-10-prompt-curation--training)
5. [UI States Summary](#5-ui-states-summary)
6. [Design Principles](#6-design-principles)
7. [Project Types & Templates](#7-project-types--templates)
   - [Coding](#coding)
   - [Writing (World Building + Story)](#writing-world-building--story)
   - [Future Templates](#future-templates)

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
| **Planning** | Feature has been created with a Refine Feature task. The planning agent (via the Refine Feature task in the Task Detail Panel) proposes a task breakdown and dependency graph; the user reviews and edits specs. Feature moves to Active when the Refine Feature task completes. |
| **Active** | Tasks are flowing through the Kanban workflow. Swimlane header shows progress. |
| **Suspended** | Auto-execution paused on this swimlane. No agents auto-run. User can still open tasks, chat with agents, and manually trigger runs. Tasks display with a visual warning treatment. On resume, auto-execution re-enables. (See F8.) |
| **Integration Test** | All tasks in the feature have completed the task workflow. A feature-level agent run verifies that all merged task outputs work together. If integration testing fails, new tasks are spawned back at Refine Spec. |
| **Complete** | Feature has passed integration testing. Swimlane moves to the completed archive. |

The feature lifecycle governs **when decomposition and re-planning happen**: specs are created and refined via the Refine Feature task during the Planning stage. Mid-flight spec changes do not require suspending — the user can edit specs at any time and run impact analysis independently (see F8).

### Task
A single unit of work within a feature. Tasks flow through the Kanban workflow stages. Each task is assigned to an **agent** (LLM or user) and executes within a specific context assembled from the project spec, feature spec, RAG history, and prior attempts.

Tasks support two forms of explicit linking:

- **`blocked_by`** — a list of `[[feature_id#task_id]]` WikiLinks (see F1 WikiLink definition). Hard blocking: a task with unmet `blocked_by` entries cannot auto-execute. When all upstream tasks reach Done, the task auto-unblocks; if the current stage has Auto-Run enabled, the agent fires automatically (see F4). Both within-feature and cross-feature blocking are supported at the task level.
- **`cross_refs`** — a list of `[[feature_id#task_id]]` WikiLinks. Soft/informational: no blocking effect. Influences context assembly by including referenced task artifacts at lower priority (see Context).

The planning agent proposes both `blocked_by` and `cross_refs` during task decomposition; the user can review and edit them in the Task Detail Panel (F3). **Circular dependency detection** is enforced on save — PCT validates the `blocked_by` graph is acyclic and rejects cycles with an error naming the offending path. **Bypass**: the user can manually run or advance a blocked task via a warning modal that lists unmet dependencies with their current status; confirming bypasses the block without removing the dependency (see F3 Stage controls).

Tasks can be added mid-flight to an active swimlane — by the user manually, or by any agent during execution. Any agent can create new tasks during execution (e.g., a code review agent spawning a bug-fix task, a planning agent spawning feature tasks, or integration test failures generating regression tasks). New tasks always enter at the Refine Spec workflow stage.

### Agent
A standalone, named configuration that defines an executor. An agent can be:
- **LLM Agent** — an AI model (local or remote) with a configured prompt template, model, and optional LoRA
- **User Agent** — the human does the work manually
- **Tool Agent** — a custom tool or script (future)
- **Image Generation Agent** — a diffusion model (HuggingFace Diffusers) that generates images from text prompts. When selected in the chat input, prompts are routed to the image generation pipeline instead of the chat pipeline.

Agents are **defined in the Project Configuration page (F10)** by combining a model (from the Model Registry), an optional LoRA adapter (from the LoRA Registry), a prompt template, and provider-specific settings. Once defined, an agent is a reusable, named entity available throughout the project — workflow stages, features, tasks, and the planning chat all reference agents by ID.

The agent assigned to a task defaults from the **workflow stage** configuration (F10), with the project's `default_agent` as fallback. The user can manually select a different agent in the chat input at any time — this selection is sticky within the same task and stage but is not a persistent task-level setting (see Chat Interface, Section 2). A task might use Claude Code for implementation but a local model for code review.

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
| **Merge** | Merge the task branch into the feature branch | Automated |
| **Full Test Suite** | Run the complete project test suite post-merge | Automated |
| **Refactoring Check** | Agent scans for refactoring opportunities, may spawn new tasks | LLM |
| **Push** | Push to remote | Automated / User |
| **Done** | Terminal stage — task is complete and archived | — |

The table above is a **reference catalog** of built-in stages. Not all stages apply to every project type. PCT provides **workflow templates** per project type with sensible defaults for which stages are active and what agents do at each stage (see Section 7 — Project Types & Templates). Workflow stages are configurable per project via the Project Configuration Page (F10).

Each stage maintains its own **per-stage context window** — the chat history between the user/agent at that stage is stored independently. When a task advances, the context window clears for the new stage; when a task is sent back, the previous stage's context is restored. See "Stage transition behavior" in the Chat Interface section for details.

### Context
The assembled information an agent receives when executing a task. Context is built from multiple layers:

1. **Project specification** — top-level goals, conventions, constraints
2. **Feature specification** — the feature this task belongs to
3. **Task specification** — what this specific task should accomplish
4. **RAG-injected history** — relevant prior task results, rejected attempts, related work from other features
5. **Chat history** — all prior chat at this task and stage, as controlled by the context window selections
6. **Upstream dependency artifacts** — `blocked_by` task artifacts and `cross_refs` task artifacts summarized if the token budget is tight

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
- **Agent selector dropdown** — user can change the agent (and therefore model) between prompts. The dropdown shows configured agents with the default agent indicated by an asterisk. The **last-used agent is sticky** — once the user selects an agent in a given context (planning chat or task), that selection persists for subsequent prompts in the same context. Default agent resolution for a fresh context follows a waterfall: workflow stage agent → project `default_agent` → first available agent.
- Text input with send/stop controls
- **Refine chip** — when an image is selected for refinement, shows a thumbnail + "Refining [image]" banner with cancel option. Auto-switches agent to imagegen.
- **Image generation routing** — when an image generation agent is selected, prompts are routed to the image generation pipeline instead of the chat API

**Section 3 — Artifact / Output** (bottom, split view):
- **Text sub-section**: Rendered markdown preview of the active text artifact. Edit button opens a rich text modal (TipTap). File path, reload, save controls. WikiLink tag strip (displays `[[feature_id#task_id]]` references found in the artifact as clickable tags). Collapsible. Artifacts are directory-based — each artifact path points to a directory containing `main.md` for text and `images/` for generated images.
- **Image sub-section**: Thumbnail grid of all generated images. Each image has hover actions: "Refine" (sends to input section) and "View" (opens full-size gallery modal). When imagegen agent is active, shows generation params (negative prompt, divergence, guidance). Progress bar during generation. Round history. Collapsible.
- **Image Gallery Modal**: Full-screen viewer (80vw × 80vh) for generated images. Left/right navigation. Image metadata (seed, round, index). Refine and Accept action buttons.

**Cross-section communication** (identical in all contexts):
- Context → Artifact: "Copy to artifact" appends chat responses to text file
- Artifact → Input: "Refine" on image pre-fills input and switches to imagegen agent
- Input → Artifact: Sending prompts generates content in the active artifact type

**Stage transition behavior** (applies to Task Detail Panel context windows):
- **Per-stage context storage** — the context window (chat history) is stored separately for each workflow stage. Each stage maintains its own conversation history with its own agent.
- **Advance on approval** — when work at a stage is approved, the task card automatically advances to the next workflow stage. Whether the next stage's agent auto-runs is controlled by the **Auto-Run toggle** on each workflow stage (F10 Workflow Stages tab). Advancing and auto-running are independent: the card always moves, but agent execution only starts automatically for stages with Auto-Run enabled (default: off for all stages).
- **Clear on advance** — when a task advances to a new stage, the context window resets to a fresh state. The new stage's agent receives a clean assembled context (project spec, feature spec, task spec, artifact, RAG-selected history) without the previous stage's conversational back-and-forth. The artifact is the handoff mechanism between stages.
- **Restore on return** — if a task is dragged back to a previous stage (e.g., from Code Review back to Implement), the context window for that stage is restored in full. All messages from the previous time the task was at that stage reappear exactly as they were. This makes stage transitions non-destructive — moving forward clears the view, moving backward restores it.
- **Carry-forward override** — optional toggle on the approval action for rare cases where the user wants the next stage's agent to see the current stage's raw conversation in addition to the assembled context.

---

### Artifact Strategy (shared foundation)

The Artifact Strategy governs how work products are organized, stored, and merged across all project types. Like the Chat Interface, it's a cross-cutting concern referenced by multiple features (F1, F3, F5, F11).

**Feature-level documents**
Each feature will have one central document.  It may have others.  The documents will be kept directly under the directory `work/{feature_id}/`.  The action that created the feature will create this directory and at least one main file as described below.  The file should have at least a main Header and feature overview.  It will also create at least one task called "Refine Feature" that is expected to be used to refine the purpose and tasks of this feature with associated sub-headers for each task.  This is not a hard limit.  The planning process may create more sections and tasks if the information is available. In addition other tasks may alter the feature by adding dependencies and/or sections/tasks.
- **Writing/content projects** produce a single document per feature (e.g., one chapter file, one adventure document) usually named `{feature_id}.md`. This document is expected to be the final work product. See Section 7 — Writing template for artifact types and initial features.
- **Code projects** will produce a `{feature_id}.md` file that acts as a specification document.  It should also create `implementation_plan.md` which will serve as a tech spec and build plan.  This can be blank and fleshed out by "Refine Feature" task.  Code source files will live under `src/` not under `work/`. See Section 7 — Coding template for workflow stages and initial features.

**Task work directory:**
Each task has a dedicated work directory at `work/{feature_id}/{task_id}/`. This directory provides naming isolation and contains all artifacts produced during the task:
- `main.md` — the primary text artifact (task output, section draft, code, etc.)
- generated images (drafts and accepted finals), with `session.json` for image generation metadata
- Additional files — any auxiliary files the user or agent creates during the task (e.g., alternative drafts, reference materials, supporting code). When the user requests output to a file other than the main feature document, it is written here for naming isolation.  This includes mermaid files or pdfs or test data that are reference/included from the main documents.

**Code Source**
- Source code for programming projects are shared artifacts that features span across.  It shall be kept under `src/`

**Work index:**
`work/INDEX.md` is the auto-generated master reference for all project artifacts (see F1). It catalogs features, tasks, and artifact paths, and is regenerated after task completion and on manual re-index.

---

### F1: Planning Window
The entry point for every project. A **Chat Interface** (see above) where the user collaborates with a planning agent to define:
- Project scope and specification
- Feature breakdown
- Initial task decomposition

The Planning Window is also used when:
- A new feature is being specified (project-level planning that creates features)
- The user wants to revise the project-level spec

The planning conversation becomes part of the project's permanent context. There is no Kanban board until planning produces features and tasks. Once the Kanban board appears, the Planning Window persists as a sidebar.

**Ideas List:**
The Planning Window's artifact (INDEX.md) maintains a running list of potential features and concepts — the project's "someday/maybe" list. Each idea is a lightweight text entry (title + brief description), not a feature — no directory, no tasks. Ideas serve as a holding area for concepts that haven't been committed to yet. When the user decides to pursue an idea, a "Create Feature" action promotes it: creates the feature directory, generates the Refine Feature task, and adds the swimlane to the Kanban board. The idea entry in INDEX.md is updated to reference the created feature.

**Main artifact — `work/INDEX.md`:**
The Planning Window's artifact section displays the **project index** — an auto-generated markdown file that serves as the master reference for all work in the project. The index contains:
- **Project overview** — top-level project spec reference
- **Feature catalog** — a header for each feature with links to feature specs
- **Task index** — organized by feature, with links to all task artifacts
- **Work products catalog** — paths to all generated artifacts (text, images)
- **Cross-references** — WikiLink support for inter-artifact connections. WikiLinks use the syntax `[[feature_id#task_id]]`, mirroring the `work/` directory structure. `[[feature_id]]` links to a feature-level artifact (`work/{feature_id}/`); `[[feature_id#task_id]]` links to a task artifact (`work/{feature_id}/{task_id}/`). WikiLinks are resolved at render time and displayed as clickable links that open the referenced artifact.

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
- Swimlane controls: suspend/resume toggle
- **Priority ordering** — swimlanes are drag-to-reorder. Position = priority. Higher = more important. Priority ordering is persisted to project configuration.
- **Auto-collapse** — swimlanes below a configurable threshold (default: top 5) are collapsed to headers only. User can expand any swimlane or adjust the threshold.
- **Swimlane collapse/expand** — each swimlane can be collapsed to save space, with state persisted across navigation
- **Dependency connector lines** — subtle dashed connector lines (optional) between dependent task cards (both within-swimlane and cross-swimlane `blocked_by` relationships). Hovering a connector highlights both endpoints and shows a tooltip with dependency direction. Collapsed swimlanes show a badge count of cross-swimlane dependencies instead of lines.
- **Completed archive** — features in the **Complete** lifecycle stage are moved to a collapsible "Completed" section at the bottom of the board, auto-collapsed by default. The section header shows the count of completed features. Expanding it reveals completed swimlanes in read-only mode (tasks visible but not draggable). Individual completed features can be expanded to inspect their task history and artifacts.
- **Filtering** — multi-select feature filter, toggles for suspended/complete feature visibility
- **Inline task creation** — add tasks directly from the swimlane header, with artifact type inferred from existing tasks in the feature
- **Task card visual indicators:**
  - Left border color indicates agent type (LLM: blue, User: green, Tool: gold)
  - **Right border color indicates notification state** (see F13): green = ready for user, red = needs attention (error/failure), yellow = consistency warning. No right border when no notification applies.
  - **Artifact type color dot** — small colored indicator showing the task's artifact type
  - Blocked tasks shown with reduced opacity and a **lock icon** overlay. Hovering the lock shows a tooltip listing unmet `blocked_by` entries as clickable WikiLinks.
  - **Bypass indicator** — after a user bypasses a blocked task (see F3 Stage controls), the lock icon changes to an unlocked/warning icon, the card displays a "Bypassed" badge, and normal opacity is restored
  - Selected/dragging tasks highlighted with blue background
- **Swimlane header controls:**
  - Feature title and lifecycle stage badge (color-coded)
  - Progress indicator (completed tasks / total tasks)
  - Add Task button
  - **Analyze dropdown** — triggers Gap Analysis, Continuity Check, or Impact Analysis (see below and F8)
  - Suspend/Resume toggle — suspended swimlanes display with a visual warning treatment (muted colors + suspended badge)
- **Feature Analysis Tools** (accessible from swimlane header):
  - **Gap Analysis** — an LLM-powered analysis that identifies missing tasks within a feature, streamed via SSE. Results include suggested tasks with title, feature, artifact type, and reasoning. Each suggestion has a one-click "Create" button. Gap Analysis may also suggest `blocked_by` relationships where ordering constraints are detected among existing tasks.
  - **Continuity Check** — verifies narrative/specification consistency within a feature, also streamed via SSE with the same suggestion format.

### F3: Task Detail Panel
Resizable slide-out panel (min 500px, max 900px, default 520px, draggable via left-edge handle) when clicking a task card. Contains a full **Chat Interface** (see above) plus a task-specific header. The three-section layout (context window, input, artifact/output) is identical to the shared Chat Interface — the only difference is that context and artifacts are scoped to a single task.

**Header section** (above the Chat Interface):
- Task title
- **Artifact type selector** — dropdown to assign/change the task's artifact type (e.g., chapter, character, timeline, code). Artifact types are configurable per project (see F10).
- Feature and task ID display
- **Dependencies section** (`blocked_by`) — tag strip showing hard-blocking dependencies as `[[feature_id#task_id]]` WikiLinks (see F1 WikiLink definition) with:
  - "Add Dependency" button opening a **DependencyPicker modal** — a feature-grouped task checklist for selecting blocking dependencies
  - Inline circular dependency detection — PCT validates the graph on each addition and rejects cycles with an error naming the path
  - Closable tags for removing dependencies
- **Cross-references section** (`cross_refs`) — tag strip showing soft/informational references as `[[feature_id#task_id]]` WikiLinks with:
  - "Add Ref" button opening a **CrossRefPicker modal** — same UI pattern as DependencyPicker
  - Closable tags for removing references
  - WikiLink syntax hint

**Task-specific artifact scoping:**
- The task is expected to update appropriate section in the main associated feature document or source code depending on project type.
- The additional artifact directory is `work/{feature_id}/{task_id}/`, containing `main.md` for text and `images/` for generated images.
- The agent selector in the chat input (Section 2) defaults to the workflow stage's configured agent but can be changed at any time during the conversation. This is a transient chat-level choice, not a persistent task setting — however, reopening the same task at the same workflow stage restores the last user-selected agent rather than reverting to the stage default.

**Stage controls:**
- Controls: Run Agent (calls agent with full context plus the prompt to update artifacts), Approve (Advance Stage), Reject (with feedback, falls into chat mode waiting on user), Stop (like chat interrupt, task falls into chat mode waiting on user), Send Back to Stage, **Bypass Block** (visible only when the task has unmet `blocked_by` — opens a warning modal listing unmet dependencies with their current status; on confirm, the task proceeds despite unmet deps; bypass is logged and the card displays a "Bypassed" badge on the Kanban board)

### F4: Agent Execution Engine
Manages the lifecycle of agent task execution:
- **Context assembly** using a tiered strategy: (1) always include project spec, feature spec, and task spec; (2) upstream dependency artifacts — `blocked_by` task artifacts at full content, `cross_refs` task artifacts summarized; (3) include latest 2 full retry attempts, summarize older ones; (4) RAG results ranked by relevance, included up to a configurable token budget
- **Context Manager** — an **optional** LLM-powered tool that intelligently summarizes, compresses, and prioritizes context to fit within model token limits. Called automatically before agent invocation, compressing context when the assembled context length reaches 75% of the target model's max context size. Also exposed as a tool that agents can invoke mid-execution (e.g., to request additional context or re-summarize). Uses a configurable model and prompt (set in F10 General tab) — remote models guided via prompt skills, local models fine-tuned with LoRA. Core PCT differentiator: intelligent context management rather than naive truncation.
- **Dependency-aware scheduling** — tasks with unmet `blocked_by` entries are excluded from the execution queue. On task completion, PCT re-evaluates all tasks listing the completed task in their `blocked_by` and unblocks those with no remaining blockers.
- **Auto-unblock + auto-run** — when a task's last `blocked_by` clears, it auto-unblocks. If the task's current workflow stage has Auto-Run enabled, the agent fires automatically. This creates a cascade effect: completing one task can trigger a chain of unblocks and agent executions across swimlanes.
- **Parallel execution** — multiple agents across different tasks/swimlanes simultaneously, subject to concurrency limits configured in F10
- **Worktree isolation** — each agent execution happens in an isolated git worktree
- **Error handling** — when an auto-executing agent fails (API error, model timeout, out-of-memory, unhandled exception), the task enters an **Error** state. The task card displays red notification treatment (see F13). Error details (error type, message, timestamp, partial output if any) are stored in the task's execution log. If a product notification email is configured (F10 General tab), an email alert is sent. The task remains at its current workflow stage — the user can inspect the error in the Task Detail Panel, adjust context, and retry. Auto-Run does not re-trigger on error — the user must manually retry or reassign.

### F5: Git Integration
Git is universal — **all project types** use git, not just code projects. Non-code projects produce text-mergeable documents (LaTeX, RTF, Markdown) that flow through the same pipeline.

**Artifact strategy:** See the Artifact Strategy shared foundation section for how work products are organized per project type. Writing tasks produce one document per feature (tasks edit assigned sections); code tasks produce files per task. All tasks work within their isolated `work/{feature_id}/{task_id}/` directory, which provides naming isolation for drafts, images, and auxiliary files.

**Worktree lifecycle:**
- **Spawn at execution start** — F4 creates a worktree from the feature branch when it dequeues a task
- **Agent works in the worktree** — CWD is the worktree root; tools and agents are unaware of the isolation (see Design Principle 7)
- **Merge back on completion** — serialized per feature branch to avoid races. Conflicts are rare when tasks edit separate sections/files; when they occur, a lightweight resolution agent handles them
- **Cleanup** — worktree removed after successful merge; preserved on failure for retry/inspection

**RAG interaction:** The RAG index (F6) covers the main tree only, not individual worktrees. Agents access their own in-progress files directly via the filesystem. When a task merges back, F4 triggers an incremental re-index of changed files so subsequent tasks see completed work.

**Integration stage:** When all tasks in a feature complete and merge, the feature enters the **Integration Test** lifecycle stage (see Feature Lifecycle). A feature-level agent run verifies that all merged outputs work together — editorial smoothing for writing projects, integration testing for code projects. This is a feature lifecycle event, not a per-task workflow stage.

### F6: RAG & Task History
Local storage with retrieval-augmented generation for surfacing relevant context:
- **What gets indexed**: work artifacts (the `work/{feature_id}/{task_id}/` directories — text, images, generated code), task execution metadata (input context, agent output, approval/rejection, user feedback), project and feature specs, planning chat history. Intermediate per-stage chat history is **not** indexed — artifacts are the durable output and the artifact is what gets indexed, not the conversational process that produced it.
- **What gets retrieved**: similar past tasks, rejected approaches (especially valuable), related work from other features, previously created artifacts (code functions, story characters, design decisions)
- **When it's used**: every agent invocation — RAG results are injected into the context assembly pipeline
- **Agent tool access**: RAG is available to agents as part of the default tool set. Agents can query the index mid-execution to pull in related artifacts, prior task results, or project context beyond what was assembled in the initial prompt.
- **User querying**: search and browse task history, filter by outcome, feature, agent, stage

### F7: Feedback & Training UI
Dedicated interface for improving agent quality over time through a full LoRA training pipeline: collecting training data from chat interactions, curating and augmenting it, kicking off LoRA training, and deploying the result back into an agent.

**Key design decisions:**
- **Context storage:** Hybrid — snapshot the full assembled context only when the user flags a message (not every turn), avoiding per-turn storage overhead while capturing exactly what the model saw
- **Training methods:** SFT + KTO in v1. No DPO (requires strict paired data). KTO handles unpaired thumbs-up/down naturally, even when the same prompt has both good and bad responses
- **Training data scope:** Project-scoped. LoRA output can be saved project-local or registered globally
- **LoRA updates:** Supported via continued fine-tuning. At training start, user chooses "create new" or "update existing" (picker shows both project-local and global registry LoRAs, filtered by compatible base model)
- **Local models only:** LoRA training targets local/HuggingFace models only. Remote API models use prompt template refinement. The UI greys out remote models in the training target selector with a tooltip
- **Training infrastructure:** PCT shells out to standard tooling (`transformers` + `peft` + `trl` for KTO) — simpler, more flexible, and benefits from upstream improvements

**F7 tab structure:**

| Tab | Purpose |
|-----|---------|
| **Training Data** | Browser + curation panel (Phase 2) |
| **Datasets** | Named collections, validation, format preview (Phase 3a) |
| **Training** | Create/update LoRA, config, monitor (Phase 3b) |
| **Evaluation** | A/B comparison of base vs. LoRA (Phase 4) |
| **Prompt Templates** | Versioned prompt template editor (applies to all models including remote) |

---

#### Phase 1: Data Collection (in Chat Interface)

Controls added to the **existing Chat Interface** message bubbles (both Planning Window and Task Detail Panel), alongside the existing Edit/Delete/Copy-to-artifact buttons:

**Per-assistant-message controls:**
- **Thumbs up / Thumbs down toggle** — flags the user→assistant turn pair
- **Annotation tag** (appears on flag) — quick category: `style`, `accuracy`, `completeness`, `format`, `instruction-following`, `other`
- **Note field** (optional) — free-text explaining what was good/bad
- **Visual indicator** — flagged messages get a colored left-border (green = positive, red = negative) and a small badge

**What gets stored per flag:**
- Reference to the chat session (task_id + stage, or planning session ID)
- Message index range (the user turn + assistant response)
- **Context snapshot** — the full assembled context the model received for this turn, captured at flag time
- Agent ID and Model ID
- Flag type (positive / negative)
- Annotation category + user note
- Timestamp

**Design note on context reconstruction:** Flagging captures exactly what the model saw at flag time. Trade-off: users can't retroactively flag old messages after specs have changed and get accurate context — acceptable since flagging should happen during or shortly after the interaction.

**Negative examples and training methods:** SFT trains on positive examples only. Negative flags in SFT serve as curation aids — the user edits the bad response into an ideal one, converting it to a positive example. KTO natively uses both positive and negative examples without requiring pairing. The same prompt can have both a thumbs-up and thumbs-down response — KTO processes them independently.

---

#### Phase 2: Training Data Browser & Curation (F7 Training Data tab)

Two-panel layout: **browser on left, detail/editor on right**.

**Browser panel (left):**
- **Table of all flagged examples** across the project
  - Columns: source (task title + stage), agent, model, flag type (thumbs icon), category tag, date, curation status (`raw` → `curated` → `in-dataset`)
  - Row click opens detail in right panel
- **Filters:** agent, model, flag type, category, feature, curation status
- **Sort:** date, category, source
- **Bulk selection** with batch actions: bulk-tag, bulk-status, bulk-add-to-dataset, bulk-delete
- **Stats bar** at top: total examples, positive/negative split, per-model counts, per-category distribution. Warnings when data volume is low (<50 examples)

**Detail / Curation panel (right):**
- **Context viewer** — collapsible panels showing the full context snapshot (system prompt, project spec, feature spec, task spec, RAG results). Read-only reference
- **Conversation excerpt** — the flagged user message + assistant response, in chat-bubble format
- **Editable response field** — user rewrites the response to be the "ideal" version. Core curation action. For negative examples in SFT mode, this converts them to positive training data. For KTO, negative examples can be used as-is or edited
- **Context trimming controls** — checkboxes to include/exclude specific context sections from the training example
- **Annotation editor** — edit category tags and notes
- **Status selector** — mark as `curated` when done
- **"Add to Dataset" button** — adds to a named dataset

**Manual example creation:**
- **"New Example" button** — create a training example from scratch (write prompt + ideal response). For teaching behavior that hasn't come up organically

**Data amplification tools** (action buttons in the curation panel, available on any flagged example):

- **"Generate Alternatives" (multi-agent):**
  - Opens a sub-panel below the flagged example
  - **Agent multi-selector** — pick which agents to run against this prompt/context (e.g., Llama-local, Mistral-local, Claude-remote)
  - Each selected agent produces a response to the same assembled context
  - Results displayed in a stacked list, each with:
    - Agent/model label
    - The generated response (scrollable)
    - **Rating controls:** thumbs up (include as positive), thumbs down (include as negative for KTO), or "Exclude" (skip — too similar or not useful)
    - **Similarity warning** — if cosine similarity to an existing dataset entry exceeds a threshold, shows "Similar to existing example" badge. User can still include if they choose
  - Rated responses become new training data entries linked to the original flag's context snapshot
  - Good for KTO: naturally produces genuine good/bad responses to the same prompt without manual pairing

- **"Generate Variations" (temperature sweep):**
  - Opens a sub-panel below the flagged example
  - **Agent selector** — single agent to use for generation
  - **Temperature spread** — configurable set of temperature values. Default: `0.1, 0.2, 0.4, 0.6, 0.8, 0.99`. User can edit, add, or remove values
  - Generates one response per temperature value (runs sequentially or in parallel depending on concurrency limits)
  - Results displayed in a list ordered by temperature, each with:
    - Temperature label + the generated response
    - Same rating controls as above (thumbs up / down / exclude)
    - Same similarity warning against existing dataset entries
  - Low temperatures → precise/conservative responses; high temperatures → creative/divergent. Gives natural diversity in training data

**Similarity detection** (shared by both amplification tools):
- Cosine similarity computed on response text against all existing examples in the target dataset
- Configurable threshold (default: 0.85) — responses above this are flagged as "too similar"
- Flagged responses default to "Exclude" but user can override to include

---

#### Phase 3: Dataset Builder & Training Kickoff

**Dataset management (F7 Datasets tab):**
- **Named datasets** — collections of curated examples grouped by purpose (e.g., "code-style-preferences", "concise-responses")
- **Dataset contents** — list of examples with remove/reorder
- **Dataset stats** — example count, avg token length, category distribution, positive/negative ratio, data volume warnings
- **Validation checks** — too short, too long (exceeds model context), duplicates, unedited negative examples (warning for SFT)
- **Format preview** — sample example in training format (ChatML, etc.)

**Training kickoff (F7 Training tab):**

Step 1 — **Create new or update existing?**
- **"New LoRA"** or **"Update existing LoRA"** toggle
- If updating: LoRA picker showing both project-local and global registry entries, filtered by compatible base model

Step 2 — **Configuration:**
- **Target base model** — dropdown from Model Registry, filtered to local/HuggingFace only (remote greyed out with tooltip)
- **Training method** — SFT or KTO. KTO auto-suggested when dataset contains negative examples. SFT auto-suggested when dataset is positive-only
- **Dataset selector** — which dataset(s) to train on
- **Training name** — name for the output LoRA (auto-suggested)
- **Hyperparameters** (collapsible, sensible defaults):
  - LoRA rank (default: 16)
  - LoRA alpha (default: 32)
  - Learning rate (default: 2e-4)
  - Epochs (default: 3)
  - Batch size (default: 4)
  - Max sequence length (auto from model context)
- **Hardware check** — detected GPU, VRAM, estimated training time
- **"Start Training" button** — disabled with tooltip if dataset empty, no GPU, or validation errors

Step 3 — **Monitor:**
- Active/completed training jobs list
- Per job: progress bar, current epoch, loss value, elapsed time, ETA
- Loss curve chart (live-updating)
- Log stream (scrollable training output)
- Cancel button with confirmation

Step 4 — **On completion: "Save where?"**
- **Project-local only** — LoRA saved to project directory
- **Register globally** — also added to the global LoRA Registry (`~/.pct/registries/`)

---

#### Phase 4: Post-Training — Evaluation & Agent Integration

**A/B evaluation (F7 Evaluation tab):**
- Select test prompts (pull from flagged examples, or write new)
- Run base model vs. base+LoRA side-by-side
- Blind mode option (don't label which is which)
- Rate each response, see aggregate scores
- **Verdict actions:** "Accept LoRA" / "Reject & Delete" / "Need More Data"

**Agent integration (on accept):**
- Check if an agent exists with this base model + this LoRA
  - If yes: show the agent, offer to update it
  - If no: prompt "Create a new agent with this LoRA?" — pre-fill agent config
- New/updated agent immediately available in all agent dropdowns

**Version history:**
- LoRA Registry tracks versions when updating an existing LoRA
- Agent config shows which version is active
- Roll back to previous version supported

---

#### F7 Data Flow Summary

```
Chat interaction
  → User flags message pair (thumbs up/down + annotation)
  → Context snapshot captured and stored with flag

F7 Training Data tab
  → User reviews, edits response to ideal, trims context
  → Marks as curated
  → OPTIONAL: Amplify data via:
     → "Generate Alternatives" — run multiple agents on same prompt, rate outputs
     → "Generate Variations" — temperature sweep on same prompt, rate outputs
     → Similarity check prevents near-duplicate flooding

F7 Datasets tab
  → User groups curated examples into named datasets
  → Validation checks pass

F7 Training tab
  → Create new or update existing LoRA
  → Select base model + training method (SFT or KTO) + dataset
  → Configure hyperparameters → Start training → Monitor
  → On completion: save project-local and/or register globally

F7 Evaluation tab
  → A/B comparison: base vs. base+LoRA
  → Accept → create/update agent with new LoRA
```

### F8: Swimlane Management
Controls for parallel workstream management, feature prioritization, and project consistency.

**Ideas List:**
See F1 Planning Window — Ideas List. The Ideas List is maintained in the Planning Window's artifact (INDEX.md) and serves as the source for feature creation via the "Create Feature" promotion action.

**Feature Priority & Ordering:**
See F2 Kanban Board — Priority ordering. Swimlane position on the board determines feature priority via drag-to-reorder.

**Feature Creation:**
Features are created either by promoting an idea from the Ideas List, or directly from the Planning Window. On creation:
1. Feature directory is created at `work/{feature_id}/`
2. A **Refine Feature** task is auto-created — this is the canonical planning mechanism for the feature
3. The swimlane appears on the Kanban board in Planning stage
4. The Refine Feature task opens in the Task Detail Panel for the user to begin spec refinement

The Refine Feature task uses the standard Task Detail Panel and workflow stages. The planning agent proposes task breakdowns as part of the spec refinement; approved tasks are created on the board. When the Refine Feature task completes, the feature transitions to Active.

**Suspend (pause toggle):**
Pauses auto-execution on a swimlane. When suspended:
- Agents with Auto-Run enabled do not start on new or waiting tasks
- Currently running agents are halted (graceful stop — agent completes current generation step, writes a checkpoint note, then stops)
- User activity is **not blocked** — the user can still open tasks, chat with agents, manually trigger agent runs, approve/reject work, and drag tasks between stages
- Tasks in suspended swimlanes display with a **visual warning treatment** (muted colors + suspended badge) so the user knows they're working in a paused feature
- Resume re-enables auto-execution; agents with Auto-Run pick up where they left off

**Project-wide Suspend:**
A global pause button that suspends all active swimlanes simultaneously. Same mechanics as per-swimlane suspend, applied globally. Resume can be global or per-swimlane.

**Impact Analysis (consistency check):**
A general-purpose mechanism for detecting when in-flight or completed work has drifted from current specs. Impact analysis is an LLM-powered agent that compares the current state of project/feature specs against each task's spec, context, and outputs.

*Trigger points:*
- **On spec edit** — when a project or feature spec is saved, PCT offers to run impact analysis on affected features
- **On merge** — after a task merges, optionally check whether the merged output shifts assumptions for other in-flight tasks
- **Ad-hoc** — user triggers "Analyze Impact" from the swimlane header (or project-wide from the Planning Window) at any time
- **On resume** — if specs changed while a swimlane was suspended, PCT prompts for impact analysis (but does not require it)

*Analysis output:*
Results are presented in a modal (similar to Gap Analysis / Continuity Check in F2), streamed via SSE. Each finding includes:
- The affected task and its current stage
- Severity: **Contradicted** (spec directly conflicts with task output/spec), **Dependency conflict** (`blocked_by` targets a deleted or moved task, or creates an indirect indefinite wait — suggested action: "Update dependencies"), **Possibly affected** (related changes that may need review), **Unchanged** (confirmed consistent)
- Explanation of the inconsistency
- Suggested action: Restart from Refine Spec, Flag for review, No action needed

*User response:*
The user reviews findings and selects per-task actions:
- **Restart** — task is sent back to Refine Spec with updated context
- **Flag** — task gets a visual indicator that it needs review but continues in its current stage
- **Dismiss** — no action, finding is acknowledged
- **Bulk actions** — "Restart A" / "Restart all contradicted or possibly affected" / "Dismiss all unchanged" / "Dismiss All" for efficiency

### F9: Session & Project Management
- **Project creation** — on first launch (or when creating a new project), PCT redirects to the **Project Configuration page (F10)** for initial setup:
  1. **Project template selector** — choose a project type template (see Section 7) that pre-populates workflow stages, default agents, artifact types, and stage prompt templates.
  2. **Project name and directory** — set the project name and select/create the project directory
  3. The user can then review and customize all template-provided defaults across the F10 tabs before proceeding to the Planning Window.
- Session persistence — close and reopen PCT without losing state
- Export/import project state

### F10: Project Configuration Page
Dedicated settings page with **seven tabs** for managing project-level configuration:

**General tab:**
- **UI Preferences** — font size slider (10–20px), persisted to localStorage
- **Project metadata** — project name, project type (from template selected at creation, read-only), project directory (read-only)
- **Re-index work artifacts** — button to scan the work directory and rebuild the RAG index
- **Planning & defaults** — planning agent selector, default agent selector (fallback for ChatInput when no stage agent is configured)
- **Context Manager** — agent selector for the Context Manager (see F4) and a default prompt template for context summarization/compression. The Context Manager is optional; when no agent is selected, context is passed to target models without compression.
- **Agent concurrency limits** — max parallel remote API agents (default: 2), max parallel local GPU agents (default: 1). Excess tasks queue until a slot opens.
- **Notification email** (optional) — product-level email address for system notifications (agent failures, merge conflicts, integration test results, training job completion). See F13.
- **SMTP Configuration** (collapsible) — SMTP server, port, username, password/app key, TLS toggle. Required for any email notifications to function. When unconfigured, email notifications are silently skipped; visual notifications (card colors, badges) still function.

**Model Registry tab:**
- View, add, edit, and remove entries in the global Model Registry. Each entry specifies a model name, **provider type** (Remote API / Local / **HuggingFace**), model identifier, context length, and provider-specific details (model file path for local/HuggingFace, API base URL for remote). For local and HuggingFace models, a **file browser** button opens a filesystem navigation modal for selecting model paths. Context length tooltip explains that 0 = use model default. The registry is global (shared across projects) and populates model dropdowns throughout the agent configuration UI.

**LoRA Registry tab:**
- View, add, edit, and remove entries in the global LoRA Registry. Each entry specifies an adapter name, the compatible base model (selected from the Model Registry), file path to weights, and a description. The UI enforces base-model compatibility — only LoRAs matching the selected model appear in dropdowns.

**Agents tab:**
- Define named agents for this project. Each agent combines: a model (dropdown from Model Registry), an optional LoRA (dropdown from LoRA Registry, filtered by selected model), an **agent type** (LLM / User / Tool / **Image Gen**), a **provider type** (Remote API / Local / **HuggingFace** / User), a prompt template, and provider-specific settings (CLI command for remote, temperature and context length overrides). Agents are standalone entities identified by ID and referenced elsewhere in the project. The configuration UI supports creating, editing, and deleting agents.
- **User agent notification settings** — User-type agents expose two additional fields:
  - **Registered user** (optional) — dropdown linking this User agent to a registered user from the Users tab
  - **Notify on waiting** toggle — when enabled, sends an email to the linked user's email address whenever a task enters a workflow stage where this agent is the assigned executor. Requires the linked user to have an email address configured and SMTP to be set up (General tab). See F13.

**Workflow Stages tab:**
- **Drag-and-drop reorderable** stage list. Each stage has:
  - **Name** — display label (auto-generates a slugified ID unless manually changed)
  - **Prompt template** — optional per-stage prompt template injected into agent context
  - **Enabled toggle** — whether this stage is active for the project
  - **Agent selector** — default executor for tasks entering this stage (user can override in the chat input at any time)
  - **Auto-Run toggle** — when enabled, the assigned agent automatically begins execution using the stage prompt template and task description when a task enters this stage. Default: off for all stages. When off, the task waits in the stage for the user to initiate the agent conversation.
  - Inline save/cancel controls for dirty edits; delete for unused stages
  - "Add Stage" button to create new custom stages
- **Template Variables** (collapsible section):
  - **Built-in variables** (read-only reference): `{{artifact}}` (full artifact content), `{{artifact_path}}` (file path), `{{task_title}}`, `{{feature_title}}`, `{{blocked_by}}` (upstream dependency artifact content from hard-blocking tasks), `{{cross_refs}}` (cross-reference context from soft-linked tasks)
  - **Custom variables** — user-defined key/description/value triples that are substituted into stage prompt templates. Keys are auto-slugified (lowercase alphanumeric).

**Artifact Types tab:**
- Define custom artifact types for task categorization. Each type has:
  - **Label** — display name (auto-generates a slugified ID)
  - **Template hint** — instructional text injected into the agent's system prompt when working on tasks of this type
- Built-in defaults are populated from the project template (see Section 7). The Writing template provides 10 artifact types; the Coding template uses the generic `text` type
- Artifact types appear as a **color-coded dot** on task cards and as a dropdown selector in the task detail panel header

**Users tab:**
- Manage registered user profiles for the project. Each user profile contains:
  - **Display name** — identifier shown in dropdowns and notifications
  - **Email address** (optional) — required for email notifications. Validated on save.
- Registered users populate the **Registered user** dropdown in User agent configuration (Agents tab)
- Users are project-scoped — multiple projects can have different user lists
- Add, edit, and remove user profiles. Removing a user unlinks them from any User agents referencing them (with confirmation)

All project-level settings persist to `pct.yaml` in the project repo. The Model Registry and LoRA Registry persist globally to `~/.pct/registries/`.

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

**Backend — provider-type behavior:**
Image generation behavior depends on the image generation agent's provider type:
- **HuggingFace / Local** — uses HuggingFace Diffusers (default model: `sd-legacy/stable-diffusion-v1-5`). Diffusers supports both HuggingFace Hub models (downloaded on demand) and local model weights on disk. Supports **text-to-image** (first round) and **image-to-image** (subsequent rounds using the selected image as source). Generates 4 images per round with configurable parameters: prompt, negative_prompt, guidance_scale, num_inference_steps, width, height, seed, divergence. Asynchronous job-based execution with polling for status and progress.
- **User** — no automated generation. The user produces images externally and copies them directly into the task's `work/{feature_id}/{task_id}/images/` directory. PCT displays images found in the directory and supports the same selection and acceptance workflow.
- **Remote API** — PCT sends the prompt to the remote API endpoint and expects image data in the response. Compatibility is not enforced — the project administrator is responsible for ensuring the remote endpoint supports image generation. Results are displayed in the same image grid UI.

**Common:**
- Image session metadata persisted per task at `work/{feature_id}/{task_id}/images/session.json`

### F12: PERT Chart
Visual dependency graph for analyzing task relationships and identifying critical paths.

**Access:**
- **Feature-scoped** — from the swimlane header Analyze dropdown (alongside Gap Analysis, Continuity Check, and Impact Analysis)
- **Project-wide** — from a top-level navigation entry; displays all features' tasks in a single graph

**Nodes:**
- Each node represents a task
- **Color** indicates workflow stage (matches Kanban column colors)
- **Shape** indicates status: completed (filled), in-progress (half-filled), blocked (outlined + lock icon), eligible (outlined, no lock)

**Edges:**
- `blocked_by` relationships rendered as **solid directed arrows** (arrow points from upstream to downstream task)
- `cross_refs` relationships rendered as **dotted lines** (toggleable, off by default)

**Critical path:**
- The longest dependency chain is highlighted in bold/red
- A summary bar displays: chain length (number of tasks), estimated bottleneck tasks, and total stages remaining on the critical path

**Filters and controls:**
- Feature multi-select filter (project-wide view)
- Status filter (completed / in-progress / blocked / eligible)
- Stage multi-select filter
- Zoom and pan controls
- Layout toggle: left-to-right (LTR) or top-to-bottom (TTB)

**Interactions:**
- Click a node to open the task in the Task Detail Panel (F3)
- Hover a node to show a task summary tooltip (title, stage, status, `blocked_by` count)
- Read-only visualization — all dependency editing happens in the Task Detail Panel (F3)

**Guaranteed DAG:** Circular dependency detection in the Task Detail Panel (F3) ensures the PERT chart is always a valid directed acyclic graph.

### F13: Notifications
PCT provides visual and email notifications to keep users informed about tasks requiring attention, agent failures, and project events. Notifications are designed to surface actionable information without requiring the user to poll the Kanban board.

**Task Card Status Colors:**
Task cards display a **right border** notification-state color, independent of the existing left-border agent-type color:

| Color | Meaning | Trigger | Clears When |
|-------|---------|---------|-------------|
| **Green** | Ready for user | Task is waiting in a stage assigned to a User agent, or Auto-Run is off and the task needs manual invocation | User begins interaction (opens task, runs agent, or advances stage) |
| **Red** | Needs attention | Agent execution failed (see F4 Error handling), agent explicitly requested human assistance, or merge conflict detected | User addresses the error (retries, reassigns, or resolves conflict) |
| **Yellow** | Consistency warning | Task flagged by Impact Analysis, Continuity Check, or Gap Analysis as contradicted or possibly affected (see F8) | User dismisses the finding or restarts the task |

When no notification condition applies, the right border is absent. Multiple conditions follow priority order: red > yellow > green (only the highest-priority color displays).

**Notification Badge:**
A numeric badge on the top-level navigation bar shows the count of unacknowledged notifications across all features. The badge is color-coded to the highest-severity unacknowledged item (red > yellow > green). Clicking the badge opens a **Notification Panel** — a dropdown list of recent notification events, each with a link to the affected task and a dismiss action. The badge count decrements as the user addresses or dismisses items.

**Notification Events:**

| Event | Visual Indicator | Email Target |
|-------|-----------------|-------------|
| Task waiting for user | Green right border | Per-user email (if User agent has Notify on waiting enabled) |
| Agent execution failure | Red right border | Product notification email |
| Agent requests assistance | Red right border | Product notification email |
| Merge conflict detected | Red right border | Product notification email |
| Consistency/impact finding | Yellow right border | — (visual only) |
| Dependency unblocked (user stage) | Green right border | Per-user email (if User agent has Notify on waiting enabled) |
| Integration test complete | Swimlane header badge (pass/fail) | Product notification email |
| Training job complete (F7) | F7 tab badge | Product notification email |

**Email Notifications:**
Email notifications are optional and require SMTP configuration in F10 General tab. Two email targets:
- **Product notification email** (F10 General tab) — receives system-level alerts: agent failures, merge conflicts, integration test results, training job completion. Single address shared across the project.
- **Per-user email** (F10 Users tab) — receives task-waiting notifications when a task enters a workflow stage assigned to that user's agent. Configured per registered user and enabled via the **Notify on waiting** toggle on the User agent (F10 Agents tab).

Email content includes: event type, task title, feature name, workflow stage, timestamp, and a deep link to open the task in PCT (local URL).

When SMTP is not configured, email notifications are silently skipped — all visual notifications (card colors, badges, notification panel) still function independently.

---

## 4. User Narrative: Building PCT with PCT

### Act 1: Project Kickoff

The user launches PCT for the first time. PCT detects an uninitialized project and redirects to the **Project Configuration Page (F10)**. The user selects the "Coding" project template (see Section 7), names the project "PCT", and reviews the pre-populated settings across the seven tabs — the Coding template's 8 workflow stages (Refine Spec through Done, Auto-Run off for all), a Claude Code agent as the default, and the generic `text` artifact type. After confirming, PCT opens the **Planning Window (F1)** — a Chat Interface with the INDEX.md artifact. No Kanban board yet.

> **User:** I want to build a Project Construction Tool. It's a Python/React app that uses LLM agents to execute project tasks on a Kanban board. Here's my rough idea...

The **planning agent** (Claude Code, selected as the project's default) engages in back-and-forth, asking about deployment model, workflow stages, project types, and agent execution. The conversation is persistent — it becomes the project's base context.

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
> Shall I create features for these?

> **User:** Yes, create features 1–3 now. Add 4–7 to the Ideas List — we'll promote them later.

For each of the three features, PCT creates a feature directory at `work/{feature_id}/`, a feature spec file, and a **Refine Feature** task. The Ideas List in INDEX.md gains four entries: Agent Execution Engine, Git Integration, RAG & Storage, Feedback UI — lightweight text entries, no directories or tasks.

### Act 2: The Kanban Appears

The Planning Window slides to a sidebar and the Kanban board (F2) materializes. Three swimlanes, each in the **Planning** lifecycle stage, each with a single task card:

```
SWIMLANE: Core Server & API                                      [Planning]
 Refine Spec | Implement | Feature Test | Code Review | User Approval | ...
 [Refine Feature]

SWIMLANE: React Frontend — Kanban                                [Planning]
 [Refine Feature]

SWIMLANE: Planning Chat UI                                       [Planning]
 [Refine Feature]
```

Each Refine Feature task sits in the **Refine Spec** workflow stage, waiting for the user to begin spec refinement.

### Act 3: Refine Feature — Task Decomposition

The user clicks the **Refine Feature** card for "Core Server & API." The Task Detail Panel (F3) slides out — a full Chat Interface scoped to this task, with the feature spec as its artifact.

The planning agent proposes a task breakdown and dependency graph:

> **Agent:** For Core Server & API, I propose the following tasks:
> 1. Define data models (no dependencies)
> 2. Design API routes (`blocked_by: [[core-server#define-data-models]]`)
> 3. Setup project scaffold (no dependencies)
>
> Here's the dependency graph and detailed specs for each...

The user reviews, edits the specs, and approves. PCT creates the three tasks on the board, each entering at **Refine Spec**. The Refine Feature task itself completes — the feature transitions from **Planning** to **Active**. The swimlane header updates:

```
SWIMLANE: Core Server & API                                       [Active]
 [Define data models]  [Design API routes (blocked)]  [Setup scaffold]
```

"Design API routes" shows with reduced opacity and a lock icon — it is blocked by "Define data models" (`blocked_by: [[core-server#define-data-models]]`) and cannot auto-execute until that task reaches Done.

### Act 4: First Agent Run — Spec Refinement

The user clicks **"Define data models"** in Refine Spec. The Task Detail Panel shows the assembled context in the inspector: project spec, feature spec, task spec — plus RAG-injected history (empty for now, this is the first task). The agent selector shows Claude Code (the Refine Spec stage's configured default).

The user clicks **Run Agent**. The agent's response streams token-by-token via SSE. It proposes SQLAlchemy ORM models. The user clicks **Reject** and provides feedback:

> **User feedback:** "Don't use SQLAlchemy. We're doing local file storage. Rethink as Pydantic models persisted to JSON files."

The rejection and feedback are stored. PCT re-runs the agent with the full retry history: original context + first attempt + rejection feedback. The agent revises its approach, proposing Pydantic models with JSON persistence. The user approves. The task advances to **Implement** — the per-stage context window clears, and the artifact (`main.md`) carries the approved spec forward.

### Act 5: Parallel Execution

"Setup scaffold" has also been refined and approved. Two tasks are now in Implement. The user also enters Implement on a manual task:

```
SWIMLANE: Core Server & API                                       [Active]
 Refine Spec        | Implement
                      [Data models] ......  Claude Code (running)
                      [Scaffold] .........  User (manual)

SWIMLANE: React Frontend — Kanban                                 [Active]
 Refine Spec        | Implement
                      [Component tree] ..  Claude Code (running)
```

F4 launches two LLM agents in parallel, each in an isolated git worktree (F5). The user works on the scaffold manually. The Kanban updates in real-time — spinning indicators on agent tasks, a user icon on the manual task.

The user clicks into the running "Data models" task and watches the agent's output stream. They notice the agent heading in a wrong direction and click **Interrupt**. The agent completes its current generation step and stops. The user adds guidance in the chat and re-runs.

**Auto-unblock cascade:** "Define data models" completes and reaches Done. PCT automatically re-evaluates downstream dependencies — "Design API routes" has its only `blocked_by` entry cleared, so it auto-unblocks. The lock icon disappears and the card regains full opacity. The user had enabled Auto-Run on the Implement stage, so the agent fires immediately on the newly unblocked task without user intervention. The Kanban board shows a chain reaction: one completion triggers the next task's execution.

**Notification in action:** Meanwhile, the auto-running agent on "Design API routes" hits an API rate limit and fails. The task card immediately gains a **red right border** (F13), and an email alert is sent to the product notification address configured in F10. The notification badge in the top nav increments. The user clicks the badge, sees the error summary, clicks through to the task, reviews the error details, and retries. The red border clears once the agent re-runs successfully.

**Bypass demo:** Meanwhile, the user notices "Design component tree" in the React Frontend swimlane is blocked by a task that won't finish soon. They click into it and see the **Bypass Block** button in the Stage controls. Clicking it opens a warning modal listing the unmet `blocked_by` entries with their current status. The user confirms — the task proceeds despite unmet dependencies. On the Kanban board, the lock icon changes to an unlocked/warning icon and the card displays a "Bypassed" badge.

**PERT chart:** Curious about the overall project shape, the user opens the **project-wide PERT chart** from the top-level navigation (F12). The graph shows all tasks across all features as a DAG. The critical path — the longest dependency chain — is highlighted in bold red, running through "Define data models" → "Design API routes" → downstream tasks. A summary bar shows the chain length and bottleneck task. The user notes that "Setup scaffold" is off the critical path and can be deferred without affecting the project timeline.

### Act 6: Code Review — Agent Reviews Agent

"Data models" completes implementation. The user approves, and the task advances through **Feature Test** (Auto-Run is off, so the user triggers the test agent manually — pytest passes) to **Code Review**.

The Code Review stage uses a **different agent** — configured in F10 to use a review-focused prompt template. The agent reviews the implementation against the spec:

> **Review Agent:** The Task model is missing a `status_history` field mentioned in the spec. The JSON serialization helper doesn't handle datetime fields.

The task stays in Code Review. The user agrees with the findings and clicks **Send Back to Stage → Implement**. The Implement stage's context window is **restored in full** — all messages from the previous implementation session reappear. The review feedback is added to the retry history. The agent receives everything: original spec, prior implementation, review feedback.

The corrected version passes review. The task advances to **User Approval**.

### Act 7: Spec Change & Impact Analysis

While tasks are flowing, the user realizes the API design needs WebSockets instead of REST polling. They open the feature spec for "Core Server & API" and edit it directly — **no suspension required** (Feature Lifecycle, line 76).

After saving, PCT offers to run impact analysis. The user accepts. PCT runs **Impact Analysis** (F8) — an LLM-powered comparison of the updated spec against each task's spec and outputs. Results stream in a modal via SSE:

> **Impact Analysis — Core Server & API:**
> - "Design API routes" — **Contradicted**: spec now requires WebSocket endpoints, task output uses REST only
> - "Setup scaffold" — **Possibly affected**: may need WebSocket dependencies added
> - "Define data models" — **Unchanged**: data models are transport-agnostic
>
> **Actions:** [Restart] [Flag] [Dismiss] per task

The user clicks **"Restart all contradicted"** — the API routes task is sent back to Refine Spec with the updated feature spec in its context. They dismiss the unchanged task and flag the scaffold for review. On the Kanban board, the flagged scaffold task now displays a **yellow right border** (F13), a persistent visual reminder that it has an unresolved consistency finding.

### Act 8: Merge Through Push

"Design component tree" (React Frontend) has passed all stages. It reaches **Merge**:

1. **Merge** — PCT merges the task's worktree branch into the feature branch. No conflicts.
2. **Full Test Suite** — the complete project test suite runs post-merge. All tests pass.
3. **Refactoring Check** — an agent scans the merged code for refactoring opportunities. It finds a duplicated utility function and spawns a new task back at Refine Spec.
4. **Push** — the user confirms, and PCT pushes to the remote.

The task card moves to the completed archive. F4 triggers an incremental RAG re-index of the changed files so subsequent agents see the completed work.

### Act 9: RAG in Action

Later, the user promotes **"Agent Execution Engine"** from the Ideas List in INDEX.md. PCT creates the feature directory, a Refine Feature task, and adds the swimlane in **Planning** stage.

The user runs the Refine Feature task. PCT's context assembly pipeline (F4) queries RAG (F6), which injects relevant history:

> *Related prior work: The "Define data models" task went through 2 iterations. The first was rejected for using SQLAlchemy — the approved approach uses Pydantic models with JSON persistence. Relevant models: Project, Feature, Task, Agent [excerpts]. The API feature was revised mid-project to use WebSockets — see updated feature spec. The "Design component tree" task produced a React component hierarchy [excerpt].*

The planning agent starts with the right assumptions because it has access to the project's full history — including the mistakes and revisions.

### Act 10: Prompt Curation & Training

After several features, the user notices agents keep proposing overly complex solutions. They open the **Feedback & Training UI (F7)**. In the Training Data tab, they browse negative examples flagged during earlier interactions, filter by the `completeness` annotation category, and spot the pattern.

First, they open the **Prompt Templates** tab and edit the project-level agent instructions:

> *"Prefer simple, minimal implementations. Avoid ORMs, complex abstractions, and over-engineering. Use Pydantic models with JSON file persistence unless explicitly directed otherwise."*

All future agent invocations inherit this updated instruction — both local and remote models.

For the local model, the user goes further. They select 5 rejected examples and 5 approved examples in the Training Data tab, curate each one (editing responses to be ideal), and add them to a dataset called "simplicity-preferences" in the Datasets tab. In the Training tab, they select the local Llama model from the Model Registry, choose KTO as the training method (auto-suggested since the dataset has both positive and negative examples), and kick off a LoRA fine-tuning run.

Training completes. In the Evaluation tab, the user runs an A/B comparison — base model vs. base+LoRA on test prompts. The LoRA consistently produces simpler, more focused responses. The user accepts the LoRA and creates a new agent combining the base model with the trained adapter. The new agent is immediately available in all agent dropdowns throughout the project.

---

## 5. UI States Summary

| State | Interface |
|-------|-----------|
| Project kickoff | Planning Window (full Chat Interface with INDEX.md artifact) — no Kanban |
| First launch (uninitialized) | Redirects to Project Configuration Page (F10) for initial project configuration |
| Planning complete | Planning Window sidebar + Kanban board (main view) |
| Task detail | Resizable slide-out Task Detail Panel (full Chat Interface scoped to task, plus header with artifact type, `blocked_by` dependencies, `cross_refs`) |
| Agent running | Live SSE streaming + streaming indicator + Interrupt button (same in both Planning Window and Task Detail) |
| Feature analysis | Modal with streaming analysis output, suggested tasks with create buttons |
| Swimlane suspended | Swimlane tasks shown with muted/warning treatment. User can still interact. Auto-execution paused. |
| Impact analysis running | Modal with streaming analysis output, per-task findings with action buttons |
| Feature integration test | Swimlane header shows integration test status; agent output streams in feature-scoped panel |
| Feedback/training | Dedicated view with 5 tabs: Training Data (browser + curation), Datasets (named collections + validation), Training (LoRA config + monitoring), Evaluation (A/B comparison), Prompt Templates (versioned editor) |
| Project configuration | Project Configuration Page (F10) with 7 tabs: General, Model Registry, LoRA Registry, Agents, Workflow Stages, Artifact Types, Users |
| PERT chart (feature) | Feature-scoped directed acyclic graph from swimlane header Analyze dropdown |
| PERT chart (project) | Project-wide directed acyclic graph from top-level navigation |
| Bypass warning | Modal listing unmet `blocked_by` dependencies when user runs a blocked task |
| Task waiting (green) | Task card green right border — ready for user interaction. Notification badge incremented. |
| Task error (red) | Task card red right border — agent failure or merge conflict. Error details in Task Detail Panel. Email sent to product notification address. |
| Task flagged (yellow) | Task card yellow right border — consistency/impact finding. Dismissable via impact analysis actions. |
| Notification panel | Dropdown from nav badge — list of recent notification events with task links and dismiss actions |

---

## 6. Design Principles

1. **Extreme transparency** — The user can always see exactly what an agent is doing, including raw LLM messages. No black boxes.
2. **User control** — Every automated action can be interrupted, overridden, or reassigned to a human. The user is always the final authority.
3. **Context continuity** — Project knowledge accumulates and is shared. Agents learn from the project's history, including mistakes.
4. **Project-type agnostic** — The core workflow (plan, decompose, execute, review, iterate) works for code, content, and creative projects alike.
5. **Local-first** — Runs on the user's machine. No cloud dependency required (though remote LLM APIs are supported).
6. **Configurable workflow** — Stages, agents, auto-advance rules, and approval gates are all configurable per project and task type. Users can override the active agent per task in the chat input.
7. **Worktree-transparent tooling** — Agents and tools operate against `$PCT_PROJECT_ROOT` (the worktree directory during execution, the main tree otherwise). Tools use relative paths or this variable, never hardcoded repo locations. This makes worktree isolation invisible to agents — they see a normal git checkout.

---

## 7. Project Types & Templates

PCT uses **project templates** to pre-populate workflow stages, artifact types, initial features, and stage prompt templates when a project is created. Templates are selected during project creation (F9) via the Project Configuration Page (F10). The selected project type is stored as read-only metadata on the project. All template-provided defaults can be customized after creation.

Templates are JSON definitions stored in a `templates/` directory and can be user-created or community-shared. PCT ships with the following built-in templates:

### Coding

For software development projects. Features produce specification documents and implementation plans under `work/`; source code lives under `src/`.

**Workflow stages (8):**

| # | Stage ID | Label | Prompt Template |
|---|----------|-------|-----------------|
| 1 | `refine-spec` | Refine Spec | — |
| 2 | `implement` | Implement | — |
| 3 | `feature-test` | Feature Test | — |
| 4 | `code-review` | Code Review | — |
| 5 | `merge` | Merge | — |
| 6 | `full-test` | Full Test | — |
| 7 | `push` | Push | — |
| 8 | `done` | Done | — |

**Artifact types:** Uses the generic `text` artifact type. No code-specific artifact types are defined yet.

**Initial feature:** A single "Project Setup" feature (`f1-project-setup`) with four tasks:
1. Set up project structure and dependencies
2. Configure linting and formatting
3. Add CI/CD pipeline
4. Write initial README

### Writing (World Building + Story)

For creative writing, world building, D&D campaigns, and narrative projects. Each feature produces a single document per feature under `work/`. The workflow stages use content-oriented names with prompt templates that reference `{{artifact}}` and `{{cross_refs}}` template variables for world consistency.

**Workflow stages (6):**

| # | Stage ID | Label | Prompt Template |
|---|----------|-------|-----------------|
| 1 | `concept` | Concept | *"Help the user brainstorm and develop the core concept. Read {{artifact}} if it exists and suggest expansions."* |
| 2 | `outline` | Outline | *"Help structure and outline the content. Reference {{cross_refs}} for world consistency."* |
| 3 | `draft` | Draft | *"Write or expand the draft. Use {{artifact}} as the working document. Reference {{cross_refs}} for world consistency."* |
| 4 | `revise` | Revise | *"Review {{artifact}} for quality, consistency, and completeness. Cross-check against {{cross_refs}}. Suggest specific improvements."* |
| 5 | `polish` | Polish | *"Final polish of {{artifact}}. Fix grammar, improve prose, ensure consistency with {{cross_refs}}."* |
| 6 | `done` | Done | — |

**Artifact types (10):**

| ID | Label | Template Hint (summary) |
|----|-------|------------------------|
| `timeline` | Timeline & History | Chronological events, cause-and-effect, historical context |
| `location` | Location | Physical description, atmosphere, history, inhabitants |
| `character` | Character | Appearance, personality, motivations, backstory, relationships |
| `faction` | Faction / Organization | Founding history, goals, structure, members, alliances |
| `magic-system` | Magic & Religion | Rules, limitations, source of power, cultural attitudes |
| `technology` | Technology | Function, access, societal impact, limitations |
| `item` | Item / Artifact | Physical description, origin, powers, significance |
| `story-arc` | Story Arc | Premise, plot points, character involvement, themes |
| `chapter` | Chapter | Narrative prose, pacing, dialogue, plot advancement |
| `text` | Text | Generic (no template hint) |

Each artifact type includes a `template_hint` — instructional text injected into the agent's system prompt when working on tasks of that type. Template hints also instruct agents to use `[[feature_id#task_id]]` WikiLinks for cross-referencing world entities.

**Initial features (7):**

| Feature ID | Title | Tasks | Default Artifact Type |
|------------|-------|-------|-----------------------|
| `f0-timeline` | Timeline & History | Establish world chronology | `timeline` |
| `f1-locations` | Locations | Define major regions; Detail key cities | `location` |
| `f2-characters` | Characters | Create protagonist profile; Create antagonist profile | `character` |
| `f3-factions` | Factions & Organizations | Outline major factions; Define faction relationships | `faction` |
| `f4-magic-religion` | Magic & Religion | Define magic system rules; Outline religious traditions | `magic-system` |
| `f5-technology` | Technology | Define technology level and key inventions | `technology` |
| `f6-items` | Items & Artifacts | Catalog significant items and their origins | `item` |

### Future Templates

The product spec envisions additional templates: **D&D Campaign**, **Business Deck**, **Research Paper**, and a **Blank** template. These are not yet implemented. New templates can be added by defining entries in the templates directory and registering them in the project type selector.

**Template structure (JSON):**
Each template defines:
- `stages` — list of workflow stage configurations (ID, label, enabled, agent, optional prompt template)
- `initial_feature` or `initial_features` — one or more features with pre-populated tasks and artifact types
- Artifact type defaults (associated with the project type, not embedded in the template JSON directly)
