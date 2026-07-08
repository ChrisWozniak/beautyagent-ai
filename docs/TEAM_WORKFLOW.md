# Team Workflow

This project is built by two cooperating builders who share the same GitHub repository.

## GitHub Access

Both builders should be added to the GitHub repository as collaborators with the same role.

Recommended role:

- Write access for Jillian
- Write access for Christopher

GitHub access is controlled on the repository, not by local folders. If both builders have Write access to the repository, both can read, edit, commit, and push changes to all files in `main`.

## Working Areas

Jillian mainly works in:

- `frontend/`
- `docs/UI_NOTES.md`
- `shared/sample_response.json`

Christopher mainly works in:

- `backend/`
- `backend/app/tools/`
- `backend/app/agent/`
- `backend/app/data/`
- `docs/API_CONTRACT.md`
- `shared/sample_request.json`
- `shared/sample_response.json`

## Shared Files

Files in `shared/` and API-related docs should be treated as shared contract files. Changes to those files should be reviewed by both builders before merging into `main`.

## Recommended Git Flow

1. Pull the latest `main` before starting work.
2. Create a branch for each feature or fix.
3. Push the branch to GitHub.
4. Open a pull request into `main`.
5. Ask the other builder to review shared or contract changes.
6. Merge only after the branch is up to date with `main`.
