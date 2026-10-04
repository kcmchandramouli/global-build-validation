# Global build validation

Python package that checks a repository through [nox](https://nox.thea.codes/). Each check is a nox session implemented in `src/`. Run one session for a single language or tool, or run `analyze` to execute every check.

Bare `nox` does not run checks. Pass a session with `-s`. List them with `nox -l`.

## What it checks

| Files | Language or content | Tools | Nox session |
| --- | --- | --- | --- |
| `.py` | Python | black, flake8, ruff, pylint, mypy, pytest | `black`, `flake8`, `ruff`, `pylint`, `mypy`, `pytest`, or `python` for all six |
| `.md` | Markdown | markdownlint-cli2, markdown-link-check, Prettier | `markdownlint`, `markdown-link-check`, `prettier` |
| `.yml`, `.yaml` | YAML | yamllint, Prettier | `yamllint`, `prettier` |
| `.toml` | TOML | Prettier | `prettier` |
| `.tf` | Terraform | `terraform fmt`, Checkov | `terraform-format`, `terraform-validation` |
| `.jpg`, `.jpeg`, `.png`, `.gif` | Images tracked by git | unreferenced image check | `unreferenced-image-check` |
| any text | Spelling | CSpell | `cspell` |
| git branch | Branch name | configurable regular expression | `branch-name` |

## Prerequisites

- Python 3.10 or newer
- Git, for branch-name validation and the unreferenced image check
- Node.js 18 or newer, for `cspell`, `markdownlint`, `prettier`, and `markdown-link-check` (`npx` is used when the binary is not already on `PATH`)
- The Terraform CLI, for `terraform-format`

Python tools are installed into the nox virtualenv from `requirements.txt` when a session runs. Checkov is installed by the `terraform-validation` session. Node packages are declared in `package.json` and fetched by `npx` at the versions the sessions request (`cspell@6`, `prettier@3`, `markdown-link-check@3`, `markdownlint-cli2`).

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
nox -s prettier
nox -s yamllint
nox -s cspell
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
nox -s prettier -- README.md
nox -s terraform-format -- path/to/main.tf
nox -s cspell -- README.md
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
| `markdownlint` | markdownlint-cli2 using `src/share/markdownlint-cli2/.markdownlint-cli2.yaml`. Line length rule MD013 is disabled. Default glob is `**/*.md`. |
| `markdown-link-check` | Checks each `.md` file with `src/share/markdown-link-check/markdown-link-check.json`. |
| `prettier` | Formatting check for Markdown, and also for YAML and TOML. See below. |

`/tmp/markdownlint-cli2.files` overrides the Markdown file list the same way `/tmp/python.files` does for Python.

Link checking walks the tree and skips `.git`, `repos`, `__pycache__`, `.pytest_cache`, `.nox*`, and `.venv*`. Set `AUTHORIZATION_PAT` to send a Basic auth header, or set `AUTHORIZATION_TOKEN` to send that token as the `Authorization` header. With a token, HTTP 203 is no longer treated as a live status.

### YAML

`nox -s yamllint` uses `src/share/yamllint/.yamllint.yaml`. Document-start, line length, and newline checks are disabled so both LF and CRLF files pass. Helm templates under `helm/**/templates/` are ignored. The default target is the current directory.

`/tmp/yamllint.files` selects the files when you do not pass paths after `--`.

Prettier also checks `**/*.yaml` and `**/*.yml`.

### TOML

`nox -s prettier` checks `**/*.toml` together with Markdown and YAML. Config is `src/share/prettier-check/.prettierrc` (print width 88, LF line endings, prose wrap preserved). EditorConfig is not applied.

`/tmp/prettier-check.files` selects the files when you do not pass paths after `--`. An empty file skips the session. When that list is absent, unmatched globs are not an error.

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

`nox -s cspell` spell-checks text with CSpell 6. The bundled dictionary is `src/share/cspell/cspell.json`. The session writes a merged config to `/tmp/cspell.yml` that imports:

- the bundled dictionary
- `CSPELL_CONFIG_FILE`, when that variable is set
- `CSPELL_CONFIG_CONTENT_JSON`, written to `/tmp/cspell.pipeline.json` when set
- files in the workspace root whose names match `*cspell.*`

The default glob is `**`. `/tmp/cspell.files` replaces it. If the workspace root has no `*cspell.*` file, a CSpell failure is reported as a warning. If a project dictionary is present, the result follows `ERROR_AS_WARNING` (default: fail).

### Git branch

`nox -s branch-name` checks the branch name against a regular expression.

Order of the pattern:

1. `build-validation.yml` key `branch-name-validation.branch_regex`
2. environment variable `BRANCH_NAME_REGULAR_EXPRESSION`
3. the built-in pattern

Built-in pattern:

```text
^(main|master|develop|(feature|feat|fix|hotfix|release|chore)/[A-Za-z0-9._-]+)$
```

Examples that match: `main`, `develop`, `feature/gbv-v1`, `fix/bug.1`. Examples that do not: `feature/master/gbv-v1`, an empty name.

`BRANCH_TO_CHECK` supplies the name. `refs/heads/` and `refs/pull/` prefixes are removed. When `BRANCH_TO_CHECK` is empty, the session uses `git rev-parse --abbrev-ref HEAD`. A detached `HEAD` is treated as an empty name and fails the default pattern.

```bash
BRANCH_TO_CHECK=feature/gbv-v1 nox -s branch-name
BRANCH_TO_CHECK=feature/master/gbv-v1 nox -s branch-name
```

## Choosing files in CI

Positional paths after `--` always win. Otherwise a session reads a file list from `/tmp` when that file exists:

| List file | Session |
| --- | --- |
| `/tmp/python.files` | `black`, `flake8`, `ruff`, `pylint`, `mypy` |
| `/tmp/yamllint.files` | `yamllint` |
| `/tmp/markdownlint-cli2.files` | `markdownlint` |
| `/tmp/prettier-check.files` | `prettier` |
| `/tmp/cspell.files` | `cspell` |
| `/tmp/terraform-format.files` | `terraform-format` |

One path per line. A missing list means "use the session default". A list file that exists but has no paths skips the check.

## Configuration

Optional file `build-validation.yml` in the working directory. `GBV_CONFIG_FILE` points at a specific file and ignores the default name. The root key may be `build-validation` or `global-build-validation`.

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
  prettier:
    error_as_warning: false
  terraform-format:
    error_as_warning: false
  terraform-validation:
    error_as_warning: false
  unreferenced-image-check:
    error_as_warning: true
  branch-name-validation:
    error_as_warning: false
    branch_regex: "^(main|master|develop|(feature|feat|fix|hotfix|release|chore)/[A-Za-z0-9._-]+)$"
```

`upload_junit` for pylint and pytest prints `##vso[task.setvariable variable=UploadJunit]`.

## Environment variables

| Variable | Effect |
| --- | --- |
| `GBV_CONFIG_FILE` | Consumer config file to read. |
| `ERROR_AS_WARNING` | `true` or `false`. Used when the config key is absent. |
| `BRANCH_TO_CHECK` | Branch name to validate. |
| `BRANCH_NAME_REGULAR_EXPRESSION` | Branch pattern when config does not set one. |
| `CSPELL_CONFIG_FILE` | Extra CSpell config to import. |
| `CSPELL_CONFIG_CONTENT_JSON` | JSON written to `/tmp/cspell.pipeline.json` and imported. |
| `AUTHORIZATION_PAT` | Personal access token for markdown link checks. Sent as Basic auth. |
| `AUTHORIZATION_TOKEN` | Raw `Authorization` header for markdown link checks. |
| `GBV_NOXFILE` | Noxfile used by `python3 -m src.entrypoint`. |
| `GBV_DEFAULT_SESSION` | Session used when the entrypoint is started with no arguments. |
| `TF_BUILD` | When `true`, the entrypoint prints `pip freeze` and, if `npm` exists, global npm packages inside Azure log groups. |
| `DOCKER_ENTRYPOINT` | Set by the entrypoint. Sessions then use tools already on `PATH` instead of installing them into a nox virtualenv. |

## Layout

```text
src/                         Python package
src/checks/                  Check implementations, one module per area
src/share/                   Bundled black/flake8/ruff/pylint/mypy/pytest,
                             yamllint, CSpell, markdownlint, Prettier, and
                             markdown-link-check configuration
noxfile.py                   Nox sessions
requirements.txt             Python dependencies
package.json                 Node dependencies
```

| Module | Checks |
| --- | --- |
| `src/checks/python.py` | black, flake8, ruff, pylint, mypy, pytest |
| `src/checks/markup.py` | markdownlint, markdown-link-check, Prettier |
| `src/checks/yaml.py` | yamllint |
| `src/checks/terraform.py` | terraform fmt, Checkov |
| `src/checks/images.py` | unreferenced images |
| `src/checks/spelling.py` | CSpell |
| `src/checks/branch.py` | branch name |

Directories named `.git`, `repos`, `__pycache__`, and `.pytest_cache`, plus names starting with `.nox` or `.venv`, are skipped when a check walks the tree.
