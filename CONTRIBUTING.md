# Contributing guide

Thank you for your interest in contributing to this project!

Here are a few tips for getting started.

## Quickstart

This project is managed through `make` commands.

To set things up, run:

```bash
make install
```

Then, you should be able to run tests:

```bash
make test
```

And code checks:

```bash
make check
```

To run auto code formatting:

```bash
make format
```

## Releasing

- Create a release PR with the following:
  - Bump the version in `__version__.py`.
  - Update `CHANGELOG.md` with PRs since the last release. **Note**: PRs that do not alter behavior (such as docs updates, refactors, tooling updates, etc) should be ignored.
- _(Maintainers only)_ Once the release PR is reviewed and merged, create a new release on the GitHub UI, including:
  - Tag version, like `0.3.1`.
  - Release title, `Version 0.3.1`.
  - Description copied from the changelog.
- Once created, the release tag will trigger a 'deploy' job on CI, automatically pushing the new version to PyPI.
