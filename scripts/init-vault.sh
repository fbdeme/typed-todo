#!/usr/bin/env bash
#
# init-vault.sh — bootstrap a typed-todo vault.
#
# Usage: init-vault.sh [VAULT_PATH]
#   - VAULT_PATH defaults to $TYPED_TODO_VAULT or $HOME/todo
#   - Idempotent: existing files are never overwritten.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

VAULT="${1:-${TYPED_TODO_VAULT:-$HOME/todo}}"

mkdir -p "$VAULT"/{tasks,projects,areas,people,resources}

# Copy the ontology spec from the skill into the vault as a reference.
if [ ! -f "$VAULT/ontology.md" ]; then
  if [ -f "$SKILL_DIR/ontology.md" ]; then
    cp "$SKILL_DIR/ontology.md" "$VAULT/ontology.md"
  else
    echo "warning: $SKILL_DIR/ontology.md not found; vault has no spec copy" >&2
  fi
fi

# Seed the inbox.
if [ ! -f "$VAULT/inbox.md" ]; then
  cat > "$VAULT/inbox.md" <<'EOF'
# Inbox

Quick-capture buffer for items not yet structured into Task nodes.
Each line should look like:

- [ ] (t-YYYY-MMDD-NN | unassigned) <description>

IDs are reserved at capture time so promoted Tasks keep their identity.
Triage during weekly review.
EOF
fi

# Seed a minimal vault README.
if [ ! -f "$VAULT/README.md" ]; then
  cat > "$VAULT/README.md" <<'EOF'
# typed-todo vault

This is a personal task vault structured as a typed property graph.
See `ontology.md` for the formal spec.

Directory layout:

- `inbox.md`     — quick capture
- `tasks/`       — Task nodes (`t-YYYY-MMDD-NN.md`)
- `projects/`    — Project nodes
- `areas/`       — Area nodes
- `people/`      — Person nodes
- `resources/`   — Resource nodes

Operate this vault via the `typed-todo` Claude Code skill, or by hand
in any editor — the format is plain markdown + YAML frontmatter.
EOF
fi

echo "Vault ready at $VAULT"
echo
echo "Layout:"
find "$VAULT" -maxdepth 2 -mindepth 1 \( -type d -o -type f \) \
  | sort \
  | sed "s|$VAULT|  .|"
