# AGENTS.md

Purpose
-------
Document approved automated agents, prompt templates, and rules for AI-assisted changes in this repository. Use this file to make agent activity auditable and predictable.

Agents
------
- Copilot / Copilot Chat: allowed to propose code and tests, create small scaffolding files, and generate unit tests. All agent-generated edits must be reviewed by a human and must pass CI before merging.
- Other LLMs / tools: allowed only if approved in a PR and the prompt used is recorded in the PR description.

Agent rules
----------
- Always add a concise, human-readable commit message for agent changes.
- Agent-generated code must:
  - Include type annotations for functions, methods, and dataclass fields.
  - Use docstrings (Google or NumPy style) so documentation can be auto-generated.
  - Include unit tests for non-trivial behavior or any logic change.
- Do not let agents commit large binary files (images, datasets). Store sample datasets in releases or external storage.
- Staging: agent changes should be made in a feature branch and submitted as a PR with the prompt(s) used.

Prompt recording
----------------
- Any agent-run that modifies source code should include the prompt text in the PR description under a titled section `Agent prompts`.
- When possible, include the agent version or provider and date.

Review checklist (PR reviewers)
------------------------------
- Confirm all new functions/classes have type annotations.
- Confirm docstrings exist and are readable by autodoc.
- Confirm tests cover changes and pass locally.
- Confirm no secrets or large binaries were added.
- Confirm cross-platform path handling and no OS-specific assumptions.

CI gating
---------
- CI must run tests and basic linters (formatting/mypy/ruff or flake8 as configured) on agent PRs before merge.

Example prompts
---------------
- "Implement EXIF timestamp extraction in `sequence_loader.py` using Pillow; fallback to mtime; include unit tests."
- "Create a PySide6 `ImageViewer` widget showing N images in a grid with zoom and rotate; add minimal smoke test."

Contact
-------
For questions about agent policies or to approve a new automated agent, contact the repository maintainers or open an issue.