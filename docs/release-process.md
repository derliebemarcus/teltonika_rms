# Release process

Release intent is recorded with a `.changeset/*.md` file using an explicit `patch`, `minor` or `major` level.

Jenkins owns the complete release lifecycle after the normal blocking quality gates pass:

1. A green `main` build consumes pending Changesets into a version pull request.
2. Patch version pull requests may use native squash auto-merge after all required checks pass. Minor and major releases remain manual.
3. The version pull request updates the changelog, package version and integration manifest version.
4. After the version pull request merges, the next green `main` build creates the tag and GitHub Release.
5. Existing published releases remain immutable. Repair runs are idempotent and fail rather than publish incomplete content.

Release Please and GitHub Actions release publishing are not used.
