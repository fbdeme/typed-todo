#!/usr/bin/env python3
"""render-overview.py — compile a typed-todo vault into a human-readable OVERVIEW.md.

Reads the raw graph (markdown + YAML frontmatter) under a vault and emits a
single dashboard file meant for humans (and GitHub's rendered view).

- Stdlib only. No PyYAML, no dependencies.
- Deterministic: same vault state -> same output (dates only, no clock time,
  to keep git diffs quiet within a day).
- Conforms to ontology.md v1.0 (5 classes, 7 typed object properties).

Usage:
    render-overview.py [VAULT_PATH] [--output FILE] [--date YYYY-MM-DD]

    VAULT_PATH  defaults to $TYPED_TODO_VAULT or ~/todo
    --output    defaults to <vault>/OVERVIEW.md ('-' for stdout)
    --date      override "today" (for reproducible tests); default system date
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

CLASSES = ("tasks", "projects", "areas", "people", "resources")
LIST_KEYS = {"for", "blocks", "involves", "about", "tags"}


# --------------------------------------------------------------------------- #
# Frontmatter parsing (intentionally tiny — our schema is flat scalars + lists)
# --------------------------------------------------------------------------- #
def parse_frontmatter(text: str) -> dict:
    """Parse leading `---` YAML block. Supports scalars and `[a, b]` lists only."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fm: dict = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        raw = raw.strip()
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            fm[key] = [x.strip() for x in inner.split(",") if x.strip()] if inner else []
        elif key in LIST_KEYS:
            fm[key] = [raw] if raw else []
        else:
            fm[key] = raw
    return fm


def load_nodes(vault: Path) -> dict[str, list[dict]]:
    """Return {class_dir: [node, ...]} where node = frontmatter + _path/_body_len."""
    out: dict[str, list[dict]] = {c: [] for c in CLASSES}
    for cls in CLASSES:
        d = vault / cls
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            try:
                text = f.read_text(encoding="utf-8")
            except OSError as e:
                print(f"warning: cannot read {f}: {e}", file=sys.stderr)
                continue
            fm = parse_frontmatter(text)
            if not fm:
                print(f"warning: {f} has no frontmatter; skipping", file=sys.stderr)
                continue
            fm["_path"] = str(f.relative_to(vault))
            out[cls].append(fm)
    return out


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def parse_date(s: str | None):
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s[:10])
    except ValueError:
        return None


def by_id(nodes: list[dict]) -> dict[str, dict]:
    return {n.get("id", n["_path"]): n for n in nodes}


def project_progress(project_id: str, tasks: list[dict]) -> tuple[int, int]:
    """(#done, #total) for tasks whose `for` includes project_id."""
    linked = [t for t in tasks if project_id in (t.get("for") or [])]
    done = sum(1 for t in linked if t.get("status") == "done")
    return done, len(linked)


def progress_bar(done: int, total: int, width: int = 10) -> str:
    if total == 0:
        return "—"
    filled = round(width * done / total)
    return "█" * filled + "░" * (width - filled)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def render(nodes: dict[str, list[dict]], today: dt.date) -> str:
    tasks = nodes["tasks"]
    projects = nodes["projects"]
    areas = nodes["areas"]
    people = nodes["people"]
    resources = nodes["resources"]

    people_by = by_id(people)
    proj_by = by_id(projects)

    open_tasks = [t for t in tasks if t.get("status") in ("open", "in_progress")]
    done_tasks = [t for t in tasks if t.get("status") == "done"]
    archived_tasks = [t for t in tasks if t.get("status") == "archived"]

    L: list[str] = []
    w = L.append

    # ---- Header -----------------------------------------------------------
    w("# Overview")
    w("")
    w(f"_Auto-generated from the task graph by `render-overview.py` · {today.isoformat()}._")
    w("")
    w("> This file is **generated** — do not edit by hand. Edit the node files under")
    w("> `tasks/`, `projects/`, etc., then re-render. See `ontology.md` for the schema.")
    w("")

    # ---- Summary ----------------------------------------------------------
    active_projects = [p for p in projects if p.get("status") == "active"]
    w("## Summary")
    w("")
    w("| | Count |")
    w("|---|---|")
    w(f"| Active projects | {len(active_projects)} |")
    w(f"| Open / in-progress tasks | {len(open_tasks)} |")
    w(f"| Done tasks | {len(done_tasks)} |")
    w(f"| Archived tasks | {len(archived_tasks)} |")
    w(f"| Areas | {len(areas)} |")
    w(f"| People · Resources | {len(people)} · {len(resources)} |")
    w("")

    # ---- Active projects --------------------------------------------------
    w("## Active projects")
    w("")
    if not active_projects:
        w("_No active projects._")
        w("")
    else:
        # sort by due (none last), then id
        active_projects.sort(key=lambda p: (parse_date(p.get("due")) or dt.date.max, p.get("id", "")))
        for p in active_projects:
            pid = p.get("id", "?")
            done, total = project_progress(pid, tasks)
            bar = progress_bar(done, total)
            due = p.get("due")
            due_str = ""
            if due:
                d = parse_date(due)
                overdue = d and d < today
                due_str = f" · due **{due}**{' ⚠️ overdue' if overdue else ''}"
            w(f"### {pid}{due_str}")
            w("")
            if p.get("description"):
                w(p["description"])
                w("")
            if p.get("definition_of_done"):
                w(f"- **Done when:** {p['definition_of_done']}")
            w(f"- **Progress:** `{bar}` {done}/{total} tasks done")
            if p.get("in_area"):
                w(f"- **Area:** {p['in_area']}")
            sub = [c.get("id") for c in projects if c.get("subproject_of") == pid]
            if sub:
                w(f"- **Sub-projects:** {', '.join(sub)}")
            w("")

    # ---- This week & overdue ---------------------------------------------
    week_end = today + dt.timedelta(days=7)
    dated = [t for t in open_tasks if parse_date(t.get("due"))]
    soon = sorted(
        [t for t in dated if parse_date(t["due"]) <= week_end],
        key=lambda t: parse_date(t["due"]),
    )
    w("## Due this week & overdue")
    w("")
    if not soon:
        w("_Nothing due in the next 7 days._")
        w("")
    else:
        w("| Due | Task | Priority | For |")
        w("|---|---|---|---|")
        for t in soon:
            d = parse_date(t["due"])
            flag = " ⚠️" if d < today else ""
            pri = t.get("priority", "normal")
            forp = ", ".join(t.get("for") or []) or "—"
            desc = t.get("description", t.get("id", "?"))
            w(f"| {t['due']}{flag} | {desc} | {pri} | {forp} |")
        w("")

    # ---- Blocked chains ---------------------------------------------------
    # B is blocked_by A iff A.blocks contains B.id
    task_by = by_id(tasks)
    blocked_by: dict[str, list[str]] = {}
    for t in tasks:
        for tgt in t.get("blocks") or []:
            blocked_by.setdefault(tgt, []).append(t.get("id", "?"))
    open_ids = {t.get("id") for t in open_tasks}
    blocked_open = {tid: [b for b in bs if b in open_ids] for tid, bs in blocked_by.items()}
    blocked_open = {tid: bs for tid, bs in blocked_open.items() if bs and tid in open_ids}
    w("## Blocked")
    w("")
    if not blocked_open:
        w("_Nothing is blocked._")
        w("")
    else:
        for tid, blockers in sorted(blocked_open.items()):
            tdesc = task_by.get(tid, {}).get("description", tid)
            bdescs = []
            for b in blockers:
                bd = task_by.get(b, {})
                bdescs.append(f"`{b}` ({bd.get('description', '?')})")
            w(f"- **{tdesc}** ({tid}) ← blocked by {', '.join(bdescs)}")
        w("")

    # ---- By area ----------------------------------------------------------
    w("## By area")
    w("")
    area_ids = [a.get("id") for a in areas]
    if not area_ids:
        w("_No areas defined._")
        w("")
    else:
        for aid in area_ids:
            at = [t for t in open_tasks if t.get("in_area") == aid]
            ap = [p for p in active_projects if p.get("in_area") == aid]
            w(f"### {aid}")
            w("")
            if ap:
                w(f"- Projects: {', '.join(p.get('id', '?') for p in ap)}")
            if at:
                w(f"- Open tasks: {len(at)}")
                for t in at[:8]:
                    w(f"  - {t.get('description', t.get('id'))}")
            if not ap and not at:
                w("_(quiet)_")
            w("")

    # ---- Recent wins ------------------------------------------------------
    w("## Recent wins")
    w("")
    if not done_tasks:
        w("_No completed tasks yet._")
        w("")
    else:
        # sort by completed_at if present else created_at, descending
        def win_key(t):
            return t.get("completed_at") or t.get("created_at") or ""
        recent = sorted(done_tasks, key=win_key, reverse=True)[:10]
        for t in recent:
            when = (t.get("completed_at") or t.get("created_at") or "")[:10]
            w(f"- ✅ {t.get('description', t.get('id'))}" + (f" · {when}" if when else ""))
        w("")

    # ---- Needs attention (hygiene) ---------------------------------------
    no_project = [t for t in open_tasks if not (t.get("for"))]
    if no_project:
        w("## Needs triage")
        w("")
        w(f"{len(no_project)} open task(s) with no `for` project — assign or archive:")
        for t in no_project[:15]:
            w(f"- {t.get('description', t.get('id'))} ({t.get('id')})")
        w("")

    w("---")
    w("")
    w("_Graph: "
      f"{len(tasks)} tasks · {len(projects)} projects · {len(areas)} areas · "
      f"{len(people)} people · {len(resources)} resources (closed-world snapshot)._")
    w("")
    return "\n".join(L)


# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render a typed-todo vault into OVERVIEW.md")
    ap.add_argument("vault", nargs="?", help="vault path (default $TYPED_TODO_VAULT or ~/todo)")
    ap.add_argument("--output", "-o", help="output file ('-' for stdout); default <vault>/OVERVIEW.md")
    ap.add_argument("--date", help="override today's date as YYYY-MM-DD (for tests)")
    args = ap.parse_args(argv)

    vault = Path(
        args.vault or os.environ.get("TYPED_TODO_VAULT") or (Path.home() / "todo")
    ).expanduser()
    if not vault.is_dir():
        print(f"error: vault not found: {vault}", file=sys.stderr)
        return 1

    if args.date:
        try:
            today = dt.date.fromisoformat(args.date)
        except ValueError:
            print(f"error: bad --date {args.date!r}", file=sys.stderr)
            return 1
    else:
        today = dt.date.today()

    nodes = load_nodes(vault)
    text = render(nodes, today)

    if args.output == "-":
        sys.stdout.write(text)
    else:
        out = Path(args.output) if args.output else (vault / "OVERVIEW.md")
        out.write_text(text, encoding="utf-8")
        print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
