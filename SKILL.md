---
name: typed-todo
description: >
  Personal task and intention management as a typed property graph — 5 classes
  (Task, Project, Area, Person, Resource) and 7 typed object properties enforced
  by an explicit ontology. Use this skill whenever the user wants to capture,
  view, update, or review personal todos that should be cross-cutting (not
  scoped to a single project — for that, see fbdeme/docs-pattern). Triggers on
  Korean phrases like "todo 추가해줘", "할 일 추가", "오늘 할 일", "내 할일 보여줘",
  "task 만들어", "프로젝트 X 할 일", "blocked된 거 뭐 있지", "weekly review 하자",
  "이번주 회고", "review my todo"; and English phrases like "add a todo",
  "what's on my plate today", "tasks for X", "what's blocking me", "weekly
  review". Reads and writes a markdown vault at ~/todo/ (or $TYPED_TODO_VAULT).
  Always conforms to ontology.md — never invents edge types, never violates
  cardinality.
---

# typed-todo

You are operating a personal task vault structured as a typed property graph. The full specification lives in `ontology.md` next to this file (and is copied into the vault). **Read `ontology.md` once at the start of any non-trivial session and treat it as authoritative.**

## When this skill is invoked

Trigger when the user wants to:

- **Capture** a new Task, Project, Area, Person, or Resource node.
- **View** existing nodes by some filter ("today", "this week", "blocked", "for project X", "involving Alice").
- **Update** node properties (status, due, priority, description) or edges (add `blocks`, `for`, etc.).
- **Promote** an inbox line-item into a structured Task node.
- **Run a review** — weekly review, inbox triage, or project status sweep.

Do **not** trigger for:

- Per-project documentation (use `fbdeme/docs-pattern` instead).
- Knowledge/fact management about timeless concepts (that's `obsidian-wiki`).
- Calendar event creation (delegate to Google Calendar MCP if connected; this skill manages intentions, not time-blocks).

## Vault location

Resolve the vault path in this order:

1. `$TYPED_TODO_VAULT` environment variable, if set.
2. `~/todo/` (default).

If the resolved path does not exist or is missing `ontology.md`, offer to run `scripts/init-vault.sh` from this skill's directory to bootstrap. Do not silently create the vault — the user must agree.

## Before any write: read the spec

The vault's `ontology.md` is the contract. Before creating or modifying any node, confirm:

- The intended `type` is one of the 5 classes.
- Every edge you are about to write is one of the 7 object properties.
- Every edge target resolves to an existing node of the right class — or you are creating that node in the same turn.
- Cardinality is respected (e.g., `subtask_of` and `subproject_of` are `0..1`; `for` is `1..2`).
- The frontmatter has all required fields for that class.

If a write would violate the spec, **stop and ask** rather than improvising.

## Capture patterns

### New Task

When the user says "task 추가해줘: implement attention layer for EEG paper":

1. Mint ID: `t-YYYY-MMDD-NN` where `NN` is the next available counter for that day in `tasks/`.
2. Copy `templates/task.md` to `tasks/<id>.md`.
3. Fill required fields: `id`, `type: Task`, `status: open`, `created_at` (now in ISO format `YYYY-MM-DDTHH:MM`), `description` (one-line summary).
4. Infer `for` from context. If the conversation mentions a project, link to it. If unclear, **ask** rather than guess; an inbox capture without `for` is acceptable temporarily (omit the field) but flag it for triage in the next review.
5. Infer other edges (`in_area`, `involves`, `about`) only if explicit in the user's request. Do not speculate.
6. If an edge target does not yet exist (e.g., user references `[[bob]]` and `people/bob.md` is absent), ask whether to create the Person node now.

### New Project

When the user says "프로젝트 추가: ICLR 논문":

1. Mint slug from the human name (kebab-case).
2. Copy `templates/project.md` to `projects/<slug>.md`.
3. **Definition of done is required.** Always elicit this from the user; do not write a placeholder.
4. Optional: `in_area`, `subproject_of`, `due`.

### New Area / Person / Resource

Same pattern with the appropriate template. Areas are rare additions — once `research`, `health`, `admin`, etc. are in place, new Areas indicate a real life-domain shift, not a project.

### Inbox capture

For "todo 추가해" / "메모해두자" without enough structure for a full node, append a single line to `inbox.md`:

```
- [ ] (t-YYYY-MMDD-NN | unassigned) <description>
```

The ID is reserved at capture time so it can later be promoted into a `tasks/<id>.md` node without re-numbering. During review, promote inbox items into structured Tasks.

## View patterns

All views are computed at read time by walking the vault directory. No indices.

### "What should I do today?"

1. List all `tasks/*.md` with `status: open` or `status: in_progress`.
2. Sort by: `priority: high` first; within priority, by `due` ascending (no due last); within that, by `created_at` ascending.
3. Group by `for` project for readability.
4. Cap at ~10 items unless the user asks for the full list.

### "Tasks for project X"

1. Walk `tasks/*.md`; select where `for` contains `X` slug OR `for` contains a Project Y with `subproject_of: X` (transitively).
2. Show with status badges.
3. Mention completed-count and remaining-count.

### "What's blocking me?"

1. Find all Tasks with `status: open` that have something in their `blocked_by` (reverse of `blocks`). Reverse traversal: walk all Tasks, find ones whose `blocks:` list contains the candidate.
2. Root causes: tasks at the head of a `blocks+` chain (nothing blocks them).
3. Surface the chain visually.

### "Everything involving Alice"

1. Walk `tasks/*.md`; select where `involves` contains `alice`.
2. Group by `for` project.

### "What's in my Inbox?"

Just show `inbox.md` content.

## Update patterns

### Mark a task done

1. Find the task by ID or fuzzy match on description.
2. Update `status: done`. Add `completed_at: YYYY-MM-DDTHH:MM` to the body or as a frontmatter line (treated as an extension field; ontology does not require it but does not forbid it).
3. Do **not** delete the file. Done tasks stay in `tasks/` for history.
4. If the completed task was in someone else's `blocks` list, mention that those tasks are now unblocked.

### Add an edge between existing nodes

1. Confirm both nodes exist.
2. Confirm the edge type is valid (in the 7-property table) and that domain/range match.
3. Add the edge to the appropriate frontmatter field of the source node.
4. Respect cardinality. If adding a 2nd `subtask_of` to a task, refuse — that's a tree violation.

### Status transition

Task: `open → in_progress → done` (or `* → archived`). Project: `active → done` (or `archived`). Never auto-cascade — project status is independent of its tasks.

## Review patterns

### Weekly review (Sunday or user-triggered)

A guided pass through the vault. Walk in this order:

1. **Inbox triage** — go through `inbox.md` line by line. For each item: promote to a Task node, archive (move to "won't do"), or leave (still uncertain).
2. **Stale open tasks** — list open/in_progress tasks with `created_at` more than 14 days ago. For each: still relevant? still actionable? change of priority?
3. **Blocked chains** — surface root causes from "what's blocking" view. Are root blockers actually still blocked?
4. **Project status sweep** — for each `active` Project: still on track? definition_of_done still right? archive if dead.
5. **Wins** — list `status: done` tasks from the past 7 days. (Closing the loop matters.)

Output a short summary at the end: how many promoted, how many archived, what shifted.

### Daily standup (optional, on "오늘 계획" / "what's today")

Just the "today" view from above. No need for full review machinery.

## Ontology enforcement — the discipline

Things this skill must refuse, even if asked:

- Adding an edge type not in the 7-property table. ("related_to" is the most tempting; refuse.)
- Writing an edge from the wrong domain class (e.g., `Person → Task` via `involves` — wrong direction).
- Writing more than one `subtask_of` or `subproject_of`.
- Marking a Project `done` based on task completion alone, without an explicit user judgment that `definition_of_done` is met.
- Deleting a task file because it's done. Done tasks stay; archive flips `status`.
- Creating a node without the required frontmatter fields (`id`, `type`, `created_at`, `description` where applicable).

When refusing, **explain which rule applies** and offer the closest valid action.

## Style notes

- IDs and slugs are immutable. If a description changes, edit the description, not the ID.
- `description` is one line; longer notes go in the file body.
- Use ISO dates everywhere. Convert relative dates ("내일", "tomorrow", "next Monday") to absolute before writing.
- Bracket-style wikilinks in free-text body (e.g., `See [[eeg-exp1]]`) are decorative and carry no graph weight. The graph lives in frontmatter only.

## Common mistakes to avoid

1. **Inventing edges.** If the user says "this task is related to the dissertation," do not invent `related_to: dissertation`. Either it's `for: dissertation` (contribution) or `in_area: research` (domain) — pick the right one and use it.
2. **Silent project creation.** When a user references `[[foo-project]]` in a task description and no such file exists, ask before creating.
3. **Date drift.** Always re-read the system date at the start of a session before writing `created_at` or `due`.
4. **Forgetting closed-world.** "There must be a project somewhere for this" is not a valid assumption. If you can't find it, it doesn't exist; create or skip.
