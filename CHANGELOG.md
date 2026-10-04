# Changelog

## 1.0.0

Analysis is a Python package in `src/`, started only through nox sessions in `noxfile.py`.

| Code | Short description |
| --- | --- |
| `noxfile.py` | Registers one session per check, plus `python` (all Python tools) and `analyze` (every check). Bare `nox` runs nothing until you pass `-s`. |
| `src/__main__.py` | `python3 -m src` starts the same entrypoint as `python3 -m src.entrypoint`. |
| `src/entrypoint.py` | Builds the nox command (`--no-venv`) and replaces the process with it. A non-option argument is executed as a program. |
| `src/config.py` | Reads `build-validation.yml` (or `GBV_CONFIG_FILE`) and resolves `error_as_warning`. |
| `src/workspace.py` | Resolves the workspace, bundled configs under `src/share/`, and `/tmp` file lists. Positional paths win; an empty list skips the check. |
| `src/runner.py` | Turns a tool failure into a warning or a hard error, and prints GitHub and Azure annotation lines on their own. |
| `src/checks/python.py` | Runs black, flake8, ruff, pylint, mypy, and pytest. Installs the pinned tools locally and uses configs in `src/share/python-validation/`. |
| `src/checks/yaml.py` | Runs yamllint 1.35.1 with `src/share/yamllint/.yamllint.yaml`. |
| `src/checks/markup.py` | Lints Markdown with PyMarkdown, checks links over HTTP, and checks Markdown and YAML formatting with mdformat and yamlfix. |
| `src/checks/links.py` | Reads Markdown links and checks HTTP status, ignore patterns, replacements, and optional auth. |
| `src/checks/terraform.py` | Checks `terraform fmt` on `.tf` files and runs Checkov 3.2.268 for Terraform. |
| `src/checks/images.py` | Finds git-tracked `.jpg`, `.jpeg`, `.png`, and `.gif` files that no other tracked file names. |
| `src/checks/spelling.py` | Runs codespell with the bundled ignore-word list. |
| `src/checks/branch.py` | Checks the git branch against `branch_regex`, then `BRANCH_NAME_REGULAR_EXPRESSION`, then the built-in pattern. |
| `src/share/` | Checker configuration shipped with the package: flake8, ruff, mypy, pylint, pytest coverage, yamllint, codespell, yamlfix, and markdown-link-check. |
| `requirements.txt` | Python dependencies the sessions install. |
| `build-validation.yml` | Check settings for this repository: failure mode, JUnit upload, and the branch pattern. |
| `.github/workflows/analysis.yml` | Runs the configured nox sessions on GitHub Actions. |
