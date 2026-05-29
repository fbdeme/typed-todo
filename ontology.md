# Personal Task Ontology

A typed property graph for personal task and intention management.

This file is the **formal spec**. Every read or write to the vault must conform to it. When in doubt, this document wins.

## Design philosophy

- **Closed world.** If a node is not in the vault, it does not exist for our purposes. We do not assume hidden truths.
- **Property graph, not RDF.** Nodes carry typed properties; edges carry types but no properties of their own. Storage is markdown with YAML frontmatter; wikilinks are typed via the property name that holds them.
- **No reasoner.** We do not infer edges. Every relationship is written explicitly. Transitive queries (`blocks+`, `subproject_of*`) are computed at read time, not stored.
- **Explicit ontology.** The class set, property set, domain, range, and cardinality below are the entire vocabulary. Anything outside this spec is invalid.
- **Markdown source of truth.** RDF/Turtle, if ever produced, is derived and ephemeral. Never edit derived output.

## Classes (5)

| Class | Definition | Lifecycle |
|---|---|---|
| `Task` | An atomic action the user performs. Either gets done or gets archived; never split implicitly. | `open` → `in_progress` → `done` \| `archived` |
| `Project` | A finite outcome with an explicit definition-of-done. Status is owned by the project, not derived from its tasks. | `active` → `done` \| `archived` |
| `Area` | A persistent domain of life (e.g., `research`, `health`, `admin`). Never reaches a "done" state. | always live |
| `Person` | A human who participates in tasks. Identity persists across projects. | always live |
| `Resource` | An external referent — a paper, code repo, document, link, dataset. The thing a task is *about*. | always live |

## Object properties (7)

Each edge is directional and **typed**. Untyped `[[wikilink]]` references in free-text body are allowed but carry no semantic weight; only frontmatter-declared edges count.

| Property | Domain | Range | Cardinality | Semantics |
|---|---|---|---|---|
| `subtask_of` | `Task` | `Task` | `0..1` | This task is a sub-step of the parent task. Forms a tree. |
| `for` | `Task` | `Project` | `1..2` | This task contributes work toward the project's outcome. |
| `subproject_of` | `Project` | `Project` | `0..1` | This project is a structural part of a larger project. Forms a tree. |
| `in_area` | `Task` ∪ `Project` | `Area` | `0..1` | Belongs to a persistent life domain. Optional; many tasks/projects have none. |
| `blocks` | `Task` | `Task` | `0..*` | This task must finish before the target task can start. |
| `involves` | `Task` | `Person` | `0..*` | Completing this task requires the listed people. |
| `about` | `Task` | `Resource` | `0..*` | The subject the task addresses (paper, codebase, etc.). |

Edge cardinality is enforced by **writer discipline** (and the patterns in `SKILL.md`), not by tooling. The reasoner you do not have cannot save you.

### Forbidden edges

The following are explicitly **not** in the ontology:

- No generic `related_to` / `see_also` / `tag_of`. If you cannot name the semantic relation, do not write it.
- No `Task → Area` via `for`. Use `in_area`.
- No `Project → Task` reverse declarations. Edges are declared on the side stated in the Domain column.
- No edges between classes not listed in the table (e.g., `Person → Resource`).

## Datatype properties

These appear inside frontmatter as scalar values, not as wikilinks.

| Property | Domain | Range | Required? |
|---|---|---|---|
| `id` | all | string (slug; see Identifiers) | **yes** |
| `type` | all | one of `Task` / `Project` / `Area` / `Person` / `Resource` | **yes** |
| `status` | `Task`, `Project` | enum: `open` / `in_progress` / `done` / `archived` (Task); `active` / `done` / `archived` (Project) | **yes** for Task/Project |
| `priority` | `Task` | enum: `low` / `normal` / `high` | no (default `normal`) |
| `due` | `Task`, `Project` | ISO date (`YYYY-MM-DD`) | no |
| `created_at` | all | ISO datetime (`YYYY-MM-DDTHH:MM`) | **yes** |
| `description` | `Task`, `Project` | string (one-line summary; body of the file holds longer notes) | **yes** |
| `definition_of_done` | `Project` | string (the success criterion) | **yes** for Project |
| `tags` | all | list of strings (free-form labels; not typed edges) | no |

## File layout

```
~/todo/
├── ontology.md              # copy of this spec (reference)
├── inbox.md                 # quick-capture buffer for unsorted items
├── tasks/
│   └── <id>.md              # one file per Task instance
├── projects/
│   └── <slug>.md            # one file per Project
├── areas/
│   └── <slug>.md            # one file per Area
├── people/
│   └── <slug>.md            # one file per Person
└── resources/
    └── <slug>.md            # one file per Resource
```

Done/archived task files stay in `tasks/` (filtered by `status` at query time). No separate archive directory — we want closed-world over a single graph snapshot.

## Identifiers

- **Task IDs**: `t-YYYY-MMDD-NN` (e.g., `t-2026-0531-01`). `NN` is a two-digit counter starting at `01` for that day.
- **Project / Area / Person / Resource slugs**: kebab-case from the human-readable name (e.g., `eeg-wm-jepa-paper`, `research`, `alice`, `paper-attention-is-all-you-need`).
- IDs and slugs are immutable once written. Rename = new node + redirect, never silent edit.

## Frontmatter schemas

Every file begins with YAML frontmatter. Body follows after the closing `---`.

### Task

```yaml
---
id: t-2026-0531-01
type: Task
status: open
priority: normal
created_at: 2026-05-31T10:00
description: One-line summary of the action.
due: 2026-06-05            # optional
for: [eeg-wm-jepa-paper]   # 1..2 Project slugs
in_area: research          # optional, 0..1
subtask_of: t-2026-0530-02 # optional, 0..1
blocks: [t-2026-0531-02]   # optional, 0..*
involves: [alice]          # optional, 0..*
about: [attention-paper]   # optional, 0..*
tags: [implementation]     # optional
---

Free-form notes, logs, decisions go here.
```

### Project

```yaml
---
id: eeg-wm-jepa-paper
type: Project
status: active
created_at: 2026-04-12T09:00
description: Paper on JEPA for EEG working-memory decoding.
definition_of_done: Accepted to NeurIPS 2026 or comparable.
due: 2026-08-15            # optional target date
in_area: research          # optional
subproject_of: dissertation # optional, 0..1
tags: [paper, jepa]
---

Project context, scope, key decisions.
```

### Area

```yaml
---
id: research
type: Area
created_at: 2026-01-01T00:00
description: Academic research domain.
tags: []
---

What this area covers, ongoing responsibilities.
```

### Person

```yaml
---
id: alice
type: Person
created_at: 2026-02-10T00:00
description: PhD advisor; EEG/JEPA collaborator.
tags: [advisor]
---

Contact context, working preferences, etc.
```

### Resource

```yaml
---
id: attention-paper
type: Resource
created_at: 2026-03-01T00:00
description: Vaswani et al. 2017, "Attention is All You Need".
tags: [paper, transformer]
---

URL, summary, why it matters.
```

## Cardinality restrictions (formal)

A vault state is **valid** iff:

1. Every node file has `id`, `type`, `created_at`, and (for Task/Project) `description`.
2. Every Task has exactly one `status` from its enum; same for Project.
3. Every Task has 1 or 2 `for` targets, each resolving to an existing Project.
4. Every `subtask_of` / `subproject_of` resolves to an existing node of the right class, and forms no cycle.
5. Every `in_area` / `involves` / `about` target resolves to an existing node of the right class.
6. Every Project has a non-empty `definition_of_done`.
7. No edge type appears outside the seven in the table above.

A writer (skill, script, or human) must check 1–7 before committing a change.

## Status transitions

### Task
```
open ──► in_progress ──► done
  │                       │
  └──► archived ◄─────────┘
```
- `open → in_progress`: start working
- `in_progress → done`: completion
- `* → archived`: deprioritized or no longer relevant; never deleted, just marked

### Project
```
active ──► done
  │         │
  └──► archived ◄──┘
```
- Project status is **independent** of its tasks. Marking a Project `done` does not auto-update task status, and vice versa.

## Why no reasoner

OWL/RDFS reasoners shine for inference, equivalence, federation, and open-world data integration. For a single-user personal vault:

- We never federate.
- We want every claim explicit, not inferred (trust through visibility).
- Transitive queries are cheap to compute at read time over a vault of ~thousands of nodes.
- Markdown + grep is the ergonomic win.

The spec is reasoner-ready — should the need arise (e.g., `subproject_of` declared as `rdfs:subPropertyOf` of `for`), a converter to Turtle + an external SPARQL endpoint will work. That path is explicitly out of scope for daily use.

## Versioning

This file is the canonical spec at the time of vault creation. If the ontology changes:

1. Bump the version stamp below.
2. Migrate existing nodes if needed (additive changes do not require migration).
3. Update `SKILL.md` to match.

**Spec version:** `1.0` (2026-05-29)
