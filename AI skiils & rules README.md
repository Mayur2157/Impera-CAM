# AI Rules & Skills v2

A portable rules-and-skills pack for AI coding agents. Copy it into a project root and the agent inherits a consistent engineering standard: planning gates, session discipline, a frontend quality floor, Python/FastAPI/AI structure, and India DPDP handling.

**v2 exists to fix six structural problems in v1:** duplicated skill trees, no rule precedence, no distinction between requirements and preferences, hardcoded vendor model names, legal content with no expiry, and workflow rules strict enough to be routinely ignored.

## What changed from v1

| v1 | v2 |
|---|---|
| Skills duplicated in `.agents/skills/` and `.cursor/skills/` | One canonical tree in `.agents/`. Platform adapters (`.cursor/`, `.claude/`, `.github/`, `.windsurfrules`, `.clinerules`) are generated pointers. A duplicate is a build failure. |
| No conflict resolution — five always-on rules, unordered | `.agents/PRIORITY.md`: a 7-level hierarchy, rule-vs-rule tie-breakers, and a table of pre-resolved conflicts. |
| Requirements and preferences written in the same voice | Every statement is `[H<n>]` hard or `[S<n>]` soft. Enforced by the validator. |
| `text-embedding-3-small`, `chunk_size=512`, `max_iterations=10` in rule files | All in `.agents/config/defaults.md`, dated and soft. Model literals elsewhere are flagged. |
| 50KB legal reference with no expiry | `.agents/config/freshness.json` + a gate at the top of the document. Overdue legal content fails validation. |
| Review after *any* file change; explain before *every* change; exactly one question per turn | Review per coherent unit; explanation scaled to change class; 1–3 related questions per turn. |
| Two documentation systems (`agentic/` and root) with overlapping ownership | An explicit ownership table. Architecture of record has exactly one home. |
| Verification rule hardcoded to one vendor tool | Capability-based tiers; the tool is a per-project adapter and the rule is inert without one. |

## Supported AI IDEs & Tools

This pack automatically generates native pointer adapters for all major AI coding assistants:
- **VS Code (GitHub Copilot)**: `.github/copilot-instructions.md`
- **Cursor**: `.cursor/rules/*.mdc` & `.cursor/skills/*/SKILL.md`
- **Windsurf (Codeium)**: `.windsurfrules`
- **Cline & Roo Code**: `.clinerules`
- **Claude Code**: `.claude/CLAUDE.md`
- **Google Antigravity & Agentic Tools**: `AGENTS.md` (root universal open standard)

## Install

```sh
cp -r .agents AGENTS.md /path/to/your/project/
cd /path/to/your/project
.agents/scripts/sync.sh
.agents/scripts/validate.sh
```

If the project already has an `AGENTS.md`, merge only the block between `<!-- ai-rules:start -->` and `<!-- ai-rules:end -->` and leave everything else alone. All generated adapter files are additive — nothing is deleted that this pack did not create.

## Layout

```
.
├── AGENTS.md                        entry point (Antigravity & universal)
├── .agents/                         CANONICAL — the only place content lives
│   ├── PRIORITY.md                  conflict resolution hierarchy
│   ├── CONVENTIONS.md               authoring rules, hard/soft semantics
│   ├── manifest.json                machine-readable registry
│   ├── config/
│   │   ├── defaults.md              tunable tech defaults (all soft)
│   │   └── freshness.json           staleness register
│   ├── rules/
│   │   ├── core/                    precedence, minimal-change, kickoff,
│   │   │                            collaboration, verification
│   │   ├── frontend/                standards, redesign
│   │   ├── backend/                 python, fastapi
│   │   ├── ai/                      applications, accuracy
│   │   └── compliance/              dpdp
│   ├── skills/                      6 skills + references + kickoff templates
│   └── scripts/                     sync, validate, check-freshness
├── .cursor/                         GENERATED — Cursor rules & skills
├── .claude/                         GENERATED — Claude Code adapter
├── .github/                         GENERATED — VS Code (Copilot) instructions
├── .windsurfrules                   GENERATED — Windsurf rules adapter
└── .clinerules                      GENERATED — Cline & Roo Code adapter
```

## Daily use

```sh
.agents/scripts/sync.sh              # after editing anything in .agents/
.agents/scripts/validate.sh          # before committing; wire into CI
.agents/scripts/check-freshness.sh   # weekly, and before any compliance work
```

`validate.sh` checks that the manifest and filesystem agree, that frontmatter is complete and consistent, that every normative bullet carries a hard/soft marker with a unique ID, that no generated file duplicates canonical content or has been hand-edited, that tracked content is registered and not overdue, and that no vendor model identifier appears outside `defaults.md`.

## Adding a rule

1. Write `.agents/rules/<category>/<id>.md` following the format in `CONVENTIONS.md`.
2. Register it in `.agents/manifest.json`.
3. If it cites law, a vendor model, or an external standard, set `freshness: tracked` and add an entry to `.agents/config/freshness.json`.
4. `.agents/scripts/sync.sh && .agents/scripts/validate.sh`

## CI

```yaml
- name: Validate AI rules pack
  run: python3 .agents/scripts/validate.py
```

Consider a separate scheduled job on `.agents/scripts/check-freshness.py` so overdue legal content surfaces on its own rather than when someone happens to look.

## What this pack does not do

It does not make an agent's output correct, and it is not legal advice. The DPDP material is a developer reference with an expiry date; compliance claims go to counsel.
