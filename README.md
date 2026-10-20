# Global build validation

Python package that checks a repository through [nox](https://nox.thea.codes/). Each check is a nox session implemented in `src/`. Run one session for a single language or tool, or run `analyze` to execute every check.

Bare `nox` does not run checks. Pass a session with `-s`. List them with `nox -l`.

## What it checks

| Files | Language or content | Tools | Nox session |
| --- | --- | --- | --- |
| `.py` | Python | black, flake8, ruff, pylint, mypy, pytest | `black`, `flake8`, `ruff`, `pylint`, `mypy`, `pytest`, or `python` for all six |
| `.md` | Markdown | PyMarkdown, link check, mdformat | `markdownlint`, `markdown-link-check`, `format` |
| `.yml`, `.yaml` | YAML | yamllint, yamlfix | `yamllint`, `format` |
| `.tf` | Terraform | `terraform fmt`, Checkov | `terraform-format`, `terraform-validation` |
| `.jpg`, `.jpeg`, `.png`, `.gif` | Images tracked by git | unreferenced image check | `unreferenced-image-check` |
| any text | Spelling | codespell | `codespell` |
| git branch | Branch name | configurable regular expression | `branch-name` |

## Prerequisites

- Python 3.10 or newer
- Git, for branch-name validation and the unreferenced image check
- The Terraform CLI, for `terraform-format`

Python tools are installed into the nox virtualenv from `requirements.txt` when a session runs. Markdown, spelling, YAML formatting, and link checks use Python packages (`pymarkdownlnt`, `codespell`, `mdformat`, `yamlfix`, `requests`). Node.js is not required. TOML formatting is not checked.

## Install and list sessions

From the repository root:

```bash
python3 -m pip install -r requirements.txt
nox -l
```

## How to test

Run one check:

```bash
nox -s black
nox -s flake8
nox -s ruff
nox -s pylint
nox -s mypy
nox -s pytest
nox -s python
nox -s markdownlint
nox -s markdown-link-check
nox -s format
nox -s yamllint
nox -s codespell
nox -s terraform-format
nox -s terraform-validation
nox -s unreferenced-image-check
nox -s branch-name
```

Run every check. This session does not accept paths; pass paths to one session instead.

```bash
nox -s analyze
```

Limit a check to specific paths by placing them after `--`:

```bash
nox -s black -- src
nox -s flake8 -- src/config.py
nox -s yamllint -- src/share
nox -s format -- README.md
nox -s terraform-format -- path/to/main.tf
nox -s codespell -- README.md
```

`nox -s python -- src` forwards those paths to black, flake8, ruff, pylint, mypy, and pytest.

The same sessions can be started without calling nox yourself:

```bash
python3 -m src.entrypoint -s yamllint
python3 -m src.entrypoint -s black
```

If `GBV_DEFAULT_SESSION` is set and no arguments are passed, that session runs. `GBV_NOXFILE` overrides the noxfile path. The default noxfile is the one next to this repository.

### Python

| Session | What it does |
| --- | --- |
| `black` | `black --diff --check`. Directories named `repos` are excluded. |
| `flake8` | flake8 with `src/share/python-validation/flake8.ini` (line length 88, Google docstring convention). |
| `ruff` | `ruff check` with `src/share/python-validation/pyproject.toml`. The bundled config enables pydocstyle rules (`D`) only. |
| `pylint` | pylint with a `pylint.rc` in the working directory, or `src/share/python-validation/pylint.rc`. Writes `pylint.results.xml`. |
| `mypy` | mypy with the bundled `pyproject.toml`, installing missing type stubs non-interactively. |
| `pytest` | pytest with coverage (`src/share/python-validation/pytest-coverage.rc`), JUnit XML (`pytest.results.xml`), HTML coverage, a 60 second timeout, and doctests. Exit code 5 (no tests collected) is treated as success. |
| `python` | Runs the six sessions above. |

If the working directory contains `requirements.txt`, pylint and pytest install it first. If it contains `setup.py`, they also install the local package.

When `/tmp/python.files` exists, Python sessions check the paths listed there (one path per line) unless you passed paths after `--`. An empty list skips the session.

### Markdown

| Session | What it does |
| --- | --- |
| `markdownlint` | PyMarkdown. Line length rule MD013 is disabled. The default target is the current directory, searched recursively. |
| `markdown-link-check` | Python HTTP check of Markdown links, using `src/share/markdown-link-check/markdown-link-check.json`. |
| `format` | mdformat for Markdown and yamlfix for YAML. TOML files are skipped. |

`/tmp/markdownlint.files` overrides the Markdown lint file list the same way `/tmp/python.files` does for Python.

Link checking walks the tree and skips `.git`, `repos`, `__pycache__`, `.pytest_cache`, `.nox*`, and `.venv*`. Set `AUTHORIZATION_PAT` to send a Basic auth header, or set `AUTHORIZATION_TOKEN` to send that token as the `Authorization` header. With a token, HTTP 203 is no longer treated as a live status.

### YAML

`nox -s yamllint` uses `src/share/yamllint/.yamllint.yaml`. Document-start, line length, and newline checks are disabled so both LF and CRLF files pass. Helm templates under `helm/**/templates/` are ignored. The default target is the current directory.

`/tmp/yamllint.files` selects the files when you do not pass paths after `--`.

`nox -s format` also checks YAML with yamlfix and `src/share/yamlfix/pyproject.toml`. It does not add a document-start marker. `/tmp/format.files` selects Markdown and YAML files for that session. An empty list skips it. A `.toml` path is reported and not formatted.

### Terraform

| Session | What it does |
| --- | --- |
| `terraform-format` | `terraform fmt -check -diff` on each `.tf` file. Requires the Terraform CLI. |
| `terraform-validation` | Checkov 3.2.268 with `--framework terraform`, skipping `repos` and module download. |

`/tmp/terraform-format.files` selects the files for the format check. When that list is absent, the session finds `.tf` files itself and skips tool and VCS directories.

### Images

`nox -s unreferenced-image-check` lists files tracked by git and looks for `.jpg`, `.jpeg`, `.png`, and `.gif` files whose filename never appears in another tracked text file. Untracked images are not scanned.

When `error_as_warning` is unset, this check warns and exits successfully. Set it to `false` in config or `ERROR_AS_WARNING=false` to make unreferenced images fail the session.

### Spelling

`nox -s codespell` spell-checks text with codespell 2.4.1. Allowed words live in `src/share/codespell/ignore-words.txt`. `CODESPELL_IGNORE_WORDS` adds another ignore file, and so does any `*codespell*` file in the workspace root. URIs are not spell-checked. The default target is the current directory. `/tmp/codespell.files` replaces it. If the workspace root has no `*codespell*` file, a failure is reported as a warning. If a project word list is present, the result follows `codespell.error_as_warning`, then `ERROR_AS_WARNING` (default: fail).

### Git branch

`nox -s branch-name` checks `task` and `feature` branch names against a regular expression. `main`, `master`, and git tags are allowed and are not compared with that expression.

Order of the pattern:

- `build-validation.yml` key `branch-name-validation.branch_regex`
- environment variable `BRANCH_NAME_REGULAR_EXPRESSION`
- the built-in pattern

Built-in pattern for `task` and `feature` branches:

```text
^(task|feature)/(main|master|develop|maintenance|staging|prod)/[A-Za-z0-9._-]+$
```

Examples that match: `feature/master/actions_pipeline`, `task/develop/add-login`, `feature/maintenance/patch.1`. Examples that do not: `feature/gbv-v1`, an empty name. `main`, `master`, and a tag such as `v1.2.3` are allowed without matching the pattern.

`BRANCH_TO_CHECK` supplies the name. `refs/heads/` and `refs/pull/` prefixes are removed. A `refs/tags/` value, a GitHub or Azure tag ref, or a detached `HEAD` that points at a tag is allowed. When `BRANCH_TO_CHECK` is empty, the session uses `git rev-parse --abbrev-ref HEAD`. A detached `HEAD` that is not a tag is an empty name and fails the pattern.

```bash
BRANCH_TO_CHECK=feature/master/actions_pipeline nox -s branch-name
BRANCH_TO_CHECK=master nox -s branch-name
BRANCH_TO_CHECK=feature/gbv-v1 nox -s branch-name
```

## Choosing files in CI

Positional paths after `--` always win. Otherwise a session reads a file list from `/tmp` when that file exists:

| List file | Session |
| --- | --- |
| `/tmp/python.files` | `black`, `flake8`, `ruff`, `pylint`, `mypy` |
| `/tmp/yamllint.files` | `yamllint` |
| `/tmp/markdownlint.files` | `markdownlint` |
| `/tmp/format.files` | `format` |
| `/tmp/codespell.files` | `codespell` |
| `/tmp/terraform-format.files` | `terraform-format` |

One path per line. A missing list means "use the session default". A list file that exists but has no paths skips the check.

## Configuration

This repository's settings are in `build-validation.yml`. `GBV_CONFIG_FILE` points at a different file and ignores that name. The root key may be `build-validation` or `global-build-validation`.

`error_as_warning: true` turns a failed check into a warning. The session still prints GitHub Actions (`::warning::` / `::error::`) and Azure Pipelines (`##vso[task.logissue]`) lines. When the key is absent, `ERROR_AS_WARNING` is used. The usual default is a hard failure. The unreferenced image check defaults to a warning.

```yaml
build-validation:
  python:
    black:
      error_as_warning: false
    flake8:
      error_as_warning: false
    ruff:
      error_as_warning: false
    pylint:
      error_as_warning: false
      upload_junit: true
    mypy:
      error_as_warning: false
    pytest:
      error_as_warning: false
      upload_junit: true
  yamllint:
    error_as_warning: false
  markdownlint:
    error_as_warning: false
  markdown-link-check:
    error_as_warning: false
  markdown-format:
    error_as_warning: false
  yaml-format:
    error_as_warning: false
  codespell:
    error_as_warning: false
  terraform-format:
    error_as_warning: false
  terraform-validation:
    error_as_warning: false
  unreferenced-image-check:
    error_as_warning: true
  branch-name-validation:
    error_as_warning: false
    branch_regex: "^(task|feature)/(main|master|develop|maintenance|staging|prod)/[A-Za-z0-9._-]+$"
```

`upload_junit` for pylint and pytest prints `##vso[task.setvariable variable=UploadJunit]`.

## GitHub Actions

`.github/workflows/gbv_actionns_pipeline.yml` runs the sessions on every push and pull request to this repository. Each job creates a Python 3.12 virtual environment and runs `nox` inside it. Terraform sessions run only when the checkout contains a `.tf` file.

The workflow sets `BRANCH_TO_CHECK` from the pull request head branch, or from the pushed branch. Checkout leaves git in a detached `HEAD`, so the branch session does not use `git rev-parse`.

### Pull request check in another repository

`.github/workflows/gbv_pr_check.yml` is a reusable workflow. A calling repository checks out its own files and runs these sessions against that checkout. The whole tree is scanned. Checks read `build-validation.yml` from the calling repository when that file exists, and otherwise use the built-in failure mode and branch pattern.

Add this workflow in the other repository as `.github/workflows/global-build-validation.yml`. Replace `OWNER` and `REF` with this repository's owner and a branch, tag, or commit SHA.

```yaml
name: Global build validation
on:
  pull_request:
  push:
    branches:
      - "**"
permissions:
  contents: read
jobs:
  standards:
    uses: OWNER/global-build-validation/.github/workflows/gbv_pr_check.yml@REF
```

Each session is a separate check, named `standards / black`, `standards / yamllint`, and so on. After the first run, require those checks in the calling repository's branch protection rules.

Copy `build-validation.yml` into the calling repository to choose which failures are warnings and which branch names are allowed. The built-in branch pattern accepts names such as `feature/main/add-login` and rejects names such as `feature/add-login`. `main`, `master`, and tags are allowed.

Terraform jobs are added only when the calling repository tracks a `.tf` file.

This repository must allow the caller to use its workflows (repository **Settings**, **Actions**, **General**, **Access**). When this repository is public, the caller's `GITHUB_TOKEN` can clone it. When it is private, pass a token that can read it:

```yaml
jobs:
  standards:
    uses: OWNER/global-build-validation/.github/workflows/gbv_pr_check.yml@REF
    secrets:
      gbv_checkout_token: ${{ secrets.GBV_CHECKOUT_TOKEN }}
```

Optional inputs are `python-version` (default `3.12`) and `terraform-version` (default `1.9.8`).

## Environment variables

| Variable | Effect |
| --- | --- |
| `GBV_CONFIG_FILE` | Consumer config file to read. |
| `ERROR_AS_WARNING` | `true` or `false`. Used when the config key is absent. |
| `BRANCH_TO_CHECK` | Branch name to validate. |
| `BRANCH_NAME_REGULAR_EXPRESSION` | Branch pattern when config does not set one. |
| `CODESPELL_IGNORE_WORDS` | Extra codespell ignore-word file. |
| `BASEURL` | Replaces `{{BASEURL}}` in Markdown link patterns. |
| `AUTHORIZATION_PAT` | Personal access token for markdown link checks. Sent as Basic auth. |
| `AUTHORIZATION_TOKEN` | Raw `Authorization` header for markdown link checks. |
| `GBV_NOXFILE` | Noxfile used by `python3 -m src.entrypoint`. |
| `GBV_DEFAULT_SESSION` | Session used when the entrypoint is started with no arguments. |
| `TF_BUILD` | When `true`, the entrypoint prints `pip freeze` inside an Azure log group. |
| `DOCKER_ENTRYPOINT` | Set by the entrypoint. Sessions then use tools already on `PATH` instead of installing them into a nox virtualenv. |

## Layout

```text
src/                         Python package
src/checks/                  Check implementations, one module per area
src/share/                   Bundled checker configuration
noxfile.py                   Nox sessions
requirements.txt             Python dependencies
build-validation.yml         Check settings for this repository
.github/workflows/           Analysis workflow and reusable pull request check
```

| Module | Checks |
| --- | --- |
| `src/checks/python.py` | black, flake8, ruff, pylint, mypy, pytest |
| `src/checks/markup.py` | PyMarkdown, Markdown link check, mdformat, yamlfix |
| `src/checks/links.py` | HTTP checks used by `markdown-link-check` |
| `src/checks/yaml.py` | yamllint |
| `src/checks/terraform.py` | terraform fmt, Checkov |
| `src/checks/images.py` | unreferenced images |
| `src/checks/spelling.py` | codespell |
| `src/checks/branch.py` | branch name |

Directories named `.git`, `repos`, `__pycache__`, and `.pytest_cache`, plus names starting with `.nox` or `.venv`, are skipped when a check walks the tree.
