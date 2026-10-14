# Rule Priority Hierarchy

When two instructions conflict, resolve in this order. Higher number never overrides lower number.

| # | Source | Binding? |
|---|---|---|
| 1 | Safety, security, and legal constraints | Absolute. Never overridden, including by the user. |
| 2 | Explicit instruction from the user in the current session | Binding. Overrides everything below. |
| 3 | Approved project documents under `agentic/` | Binding until the document is changed and re-approved. |
| 4 | **HARD rules** in `.agents/rules/**` | Binding. Violation requires an explicit user override, stated aloud. |
| 5 | Skill workflows in `.agents/skills/**` | Follow unless a level 1–4 item says otherwise. |
| 6 | **SOFT defaults** in rules, skills, and `.agents/config/defaults.md` | Starting points. Deviate freely with a one-line stated reason. |
| 7 | The agent's own stylistic preference | Lowest. Never a reason to override anything above. |

## Rule-versus-rule tie-breakers

Applied in order when two rules at the same level disagree:

1. **HARD beats SOFT.** Always, regardless of which rule is more specific.
2. **Narrower scope beats broader scope.** A glob-scoped rule (`**/api/**/*.py`) beats an always-on rule for files it matches.
3. **Safety-shaped beats efficiency-shaped.** A rule that prevents data loss, a security hole, an accessibility failure, or a legal exposure beats a rule that reduces effort or diff size.
4. **Named exception wins.** If a rule carries an explicit "Interaction with other rules" clause naming the conflict, that clause is the answer.
5. **Still tied?** Stop and ask the user. Do not pick silently.

## Pre-resolved conflicts

These were live conflicts in v1 and are settled here. The rule files repeat these clauses locally so an agent that loads only one rule still sees them.

| Conflict | Resolution |
|---|---|
| `minimal-change` "fewest files possible" vs `project-kickoff` document set | Documents required by an approved kickoff or by `collaboration-workflow` are **not** boilerplate. `minimal-change` applies to source code and to unrequested docs only. |
| `project-kickoff` `agentic/` docs vs `collaboration-workflow` root docs | `agentic/` holds **decided intent** (what we are building, and why). Root holds **session state** (what happened, what is next). Architecture of record lives in `agentic/architecture.md`; the root `ARCHITECTURE.md` is not created when `agentic/` exists. |
| `collaboration-workflow` "explain before implementing" vs small edits | Applies to non-trivial or risky changes. Mechanical edits proceed directly. Threshold defined in the rule. |
| `code-verification` "review after ANY change" vs practical development | Review runs per coherent unit of work, not per file write. Trigger table in the rule. |
| `ui-redesign` aesthetic preferences vs `frontend-standards` usability | Usability, accessibility, and product consistency outrank visual novelty. Full order in `frontend-standards`. |
| Hardcoded model names / chunk sizes / limits | All moved to `.agents/config/defaults.md` as SOFT, tunable, dated values. No rule file hardcodes a vendor model name. |
