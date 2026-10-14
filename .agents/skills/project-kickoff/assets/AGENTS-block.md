<!-- ai-rules:start -->
## AI rules and skills

This repository uses the AI Rules & Skills pack. Canonical content is in `.agents/`; `.cursor/` and `.claude/` are generated pointers and must not be edited by hand.

Before working:

1. Read `.agents/PRIORITY.md` — the conflict-resolution hierarchy.
2. Read `.agents/CONVENTIONS.md` — what `[H<n>]` and `[S<n>]` mean. Hard rules are binding; soft defaults may be overridden with a one-line stated reason.
3. Read the applicable approved documents under `agentic/`, and `agentic/features/<feature-slug>/` for a major feature.

Treat approved requirements and rules as authoritative. If a request conflicts with them, name the conflict and ask whether to amend the documents before proceeding. Keep `agentic/memory.md`, phase statuses, and affected documents synchronized with approved changes.

Never store secrets, credentials, tokens, or personal data in project documents or memory files.
<!-- ai-rules:end -->
