# Release Publishing

PyPI releases are published from GitHub Actions with PyPI Trusted Publishing. This
avoids long-lived PyPI API tokens in local Poetry config, shell sessions, or GitHub
secrets.

## PyPI Trusted Publisher Setup

Before the first upload, create a pending Trusted Publisher on PyPI that matches this
repository's release workflow. Use a protected GitHub environment for the publishing
step so maintainers can approve releases before PyPI upload.

Maintainers should verify the exact PyPI project, repository, workflow filename, and
environment values against the release workflow before publishing.

PyPI pending publishers create the project on first successful publish. They do not
reserve the project name before that first publish.

## GitHub Release Flow

1. Ensure `pyproject.toml` contains the release version.
2. Ensure the Git tag is exactly the version or the version prefixed with `v`, for
   example `1.5.0` or `v1.5.0`.
3. Create and publish a GitHub Release for that tag.
4. GitHub Actions runs the release workflow.
5. The workflow builds the source distribution and wheel, checks them with Twine, and
   publishes them to PyPI through the protected GitHub publishing environment.

The workflow fails if the GitHub release tag does not match the version in
`pyproject.toml`.

## Local Preflight Script

`release.sh` is now a local pre-release check only. It verifies the version and tag,
installs dependencies, optionally runs tests, and builds local artifacts in `dist/`.

It does not publish to PyPI and does not deploy documentation.

```bash
./release.sh
RUN_TESTS=1 ./release.sh
```

Use the GitHub Release flow for the actual PyPI upload.
