# typed-todo

A [Claude Code](https://claude.com/claude-code) skill for personal task management as a **typed property graph**.

Instead of flat checklists, every Task is a node with typed edges to Projects, Areas, People, and Resources. Five classes, seven object properties, explicit cardinality — written down once in [`ontology.md`](./ontology.md), enforced by the skill on every read and write.

## Philosophy

- **Capture-then-structure.** New items can land flat (`inbox.md`) and get promoted later. The graph is built deliberately, not by autocomplete.
- **Closed-world, single-user.** If a node is not in the vault, it does not exist. No hidden inferences.
- **Markdown source of truth.** Plain `.md` files with YAML frontmatter, editable by hand or by Claude. No DB, no reasoner, no daemon.
- **Explicit ontology.** Every relationship has a named type. No generic `related_to`. If you cannot name the relation, you cannot write it.

## Install (per-project)

```bash
mkdir -p .claude/skills/typed-todo
curl -sL https://github.com/fbdeme/typed-todo/archive/main.tar.gz \
  | tar xz -C .claude/skills/typed-todo --strip-components=1
```

## Install (user-global)

```bash
mkdir -p ~/.claude/skills/typed-todo
curl -sL https://github.com/fbdeme/typed-todo/archive/main.tar.gz \
  | tar xz -C ~/.claude/skills/typed-todo --strip-components=1
```

## Bootstrap a vault

After installing the skill, create the vault at `~/todo/` (or set `$TYPED_TODO_VAULT` to override):

```bash
~/.claude/skills/typed-todo/scripts/init-vault.sh
```

The script is idempotent — re-running it never overwrites existing files.

## Invoking the skill

Natural-language triggers (Korean and English both work):

| Intent | Examples |
|---|---|
| Capture | `todo 추가해줘`, `task 만들어`, `add a todo`, `프로젝트 추가` |
| View | `오늘 할 일`, `내 할일 보여줘`, `what's on my plate`, `tasks for X` |
| Update | `이 task done 표시해`, `mark done`, `add a blocker` |
| Review | `weekly review 하자`, `이번주 회고`, `triage my inbox` |

The skill auto-resolves the vault path from `$TYPED_TODO_VAULT` or defaults to `~/todo/`, reads `ontology.md`, and writes only edges/properties the spec allows.

## The ontology at a glance

### Classes

| Class | Lifecycle |
|---|---|
| `Task` | `open` → `in_progress` → `done` \| `archived` |
| `Project` | `active` → `done` \| `archived` |
| `Area` | always live |
| `Person` | always live |
| `Resource` | always live |

### Object properties

| Property | Domain | Range | Cardinality |
|---|---|---|---|
| `subtask_of` | Task | Task | 0..1 |
| `for` | Task | Project | 1..2 |
| `subproject_of` | Project | Project | 0..1 |
| `in_area` | Task ∪ Project | Area | 0..1 |
| `blocks` | Task | Task | 0..* |
| `involves` | Task | Person | 0..* |
| `about` | Task | Resource | 0..* |

Full definitions, frontmatter schemas, and restrictions: [`ontology.md`](./ontology.md).

## How it differs from other tools

- **vs. flat checklists / todo.txt:** typed edges, queryable structure, project/area distinction.
- **vs. Notion / Obsidian databases:** plain markdown, git-friendly, no proprietary format, no app to launch.
- **vs. [`fbdeme/docs-pattern`](https://github.com/fbdeme/docs-pattern):** docs-pattern is per-project (`docs/todo.md` inside one repo); typed-todo is cross-project personal management.
- **vs. [obsidian-wiki](https://github.com/Ar9av/obsidian-wiki):** obsidian-wiki manages durable knowledge (facts, concepts, distilled from sources); typed-todo manages intentions (actions, outcomes, time-bound). Both are markdown vaults, but the object types and lifecycles are fundamentally different.

## Why no reasoner

OWL/RDFS reasoning is overkill for a single-user vault of a few thousand nodes. Markdown + grep + the user's own discipline handles 95% of queries. The ontology *is* reasoner-ready — should you ever want a SPARQL endpoint, the spec maps cleanly to RDF. That path is explicitly out of scope for daily use; see the note in `ontology.md`.

## License

MIT — see [`LICENSE`](./LICENSE).
