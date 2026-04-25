# T1 File Cleanup Safety Rules

- Treat delete, move, and overwrite operations as safety-sensitive.
- If file-selection criteria are ambiguous, require clarification before execution.
- Preview matched paths before deletion when the task involves removal.
- Refuse to overwrite existing files unless the user explicitly authorizes it.
- Respect tool constraints in the task schema.
