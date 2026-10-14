# Release checklist

Use this checklist from a clean `main` checkout. Replace `v1.0.0` when preparing a later release.

## Candidate validation

- [ ] Confirm `git status --short` is empty and `main` matches `origin/main`.
- [ ] Confirm CI and CodeQL pass on the release-preparation pull request.
- [ ] Run `docker compose up -d --build --wait`.
- [ ] Run `python -m pytest -q` from an environment containing `backend/requirements-dev.txt`.
- [ ] Run `npm ci`, `npm run typecheck`, `npm run build`, `npm audit --audit-level=high`, and `npm run test:e2e` in `frontend/`.
- [ ] Run the safe demo and verify the generated investigation contains TEST-NET telemetry and MITRE context.
- [ ] Review `CHANGELOG.md`, the README screenshots, and the animated walkthrough.

## Publish

```bash
git tag -s v1.0.0 -m "Insidi_OS v1.0.0"
git push origin v1.0.0
```

If signed tags are not configured, use an annotated tag with `git tag -a` and document that choice in the release notes. Pushing the tag triggers the release workflow, which creates versioned source archives and `SHA256SUMS`.

## Post-release verification

- [ ] Confirm the GitHub release is published from the expected commit.
- [ ] Download every release asset and verify it against `SHA256SUMS`.
- [ ] Extract one archive into a clean directory and repeat the Docker Compose smoke test.
- [ ] Confirm the release and demo links render correctly from the repository landing page.
