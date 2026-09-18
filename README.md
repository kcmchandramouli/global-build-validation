# Global build validation

Independent pull request checks for Python, Markdown, YAML, TOML, Terraform, spelling, images, and branch names. One repository provides:

- Checker **container images**
- **Azure Pipelines** templates
- **GitHub Actions** reusable workflows
- Optional **Helm / KEDA** Azure Pipelines agents

No vendor org names, private registries, or internal Ansible roles are required. Default CI uses container jobs on hosted runners.

## What it checks

| Files | Tools |
| --- | --- |
| `.py` | black, flake8, ruff, pylint, mypy, pytest |
| `.md` | markdownlint-cli2, markdown-link-check, Prettier |
| `.yml` / `.yaml` | yamllint, Prettier |
| `.toml` | Prettier |
| `.tf` | `terraform fmt`, Checkov |
| `.jpg` `.jpeg` `.png` `.gif` | unreferenced image check |
| any text | CSpell |
| git branch | configurable regex |

On a pull request the pipeline lists changed files and runs only matching checks. CSpell and branch-name validation always run.

## Layout

```text
images/                      Checker Dockerfiles (Ubuntu 22.04)
azure-pipelines/             ADO validation, image build, helm lint
.github/workflows/           GitHub Actions equivalents
helm/agent/                  Optional KEDA ScaledJob for ADO agents
helm/secrets/                Example secrets chart (real values are gitignored)
gitops/agents/               Argo CD ApplicationSet placeholders
config/                      Example consumer and platform config
scripts/                     Local docker runner
tests/terraform-sample/      Fixture for Terraform checks
```

## Consumer configuration

Copy [config/build-validation.example.yml](config/build-validation.example.yml) to `build-validation.yml` in the repository you want checked. Each tool can set `error_as_warning`. Branch regex is overridable:

```yaml
build-validation:
  branch-name-validation:
    branch_regex: "^(main|master|develop|(feature|feat|fix|hotfix|release|chore)/[A-Za-z0-9._-]+)$"
```

Platform placeholders (registry, ADO org, pool, Helm namespace) live in [config/platform.example.yml](config/platform.example.yml).

## Build images

Build context is the repository root.

```bash
pip install -r requirements-dev.txt
nox -s list_images
nox -s build_image -- yamllint.v1
# or
nox -s build_all
```

GitHub Actions workflow [`.github/workflows/build-images.yml`](.github/workflows/build-images.yml) pushes tags to `ghcr.io/<github.repository>:<tag>`.

Azure Pipelines [azure-pipelines/pipeline.build-images.yml](azure-pipelines/pipeline.build-images.yml) uses `Docker@2`. Set parameters `imageRepository` and `dockerRegistryServiceConnection`.

Image tags are listed in [images/catalog.yml](images/catalog.yml).

## Test locally (no Docker)

```bash
pip install -r requirements-dev.txt
nox -s test
```

Point checkers at a specific config file with `GBV_CONFIG_FILE=/path/to/build-validation.yml`.

Run Python checkers against this checkout without building images (install the tools from `images/python-validation/requirements.txt` first):

```bash
nox -f images/python-validation/noxfile.py -s black flake8 ruff -- .
python images/unreferenced-image-check/check_unreferenced_image.py
```

## Run checker images locally

Requires Docker. `nox -s run_check` works on Windows and Unix; `scripts/run-image.sh` is Unix-only.

```bash
# optional: local docker tags
# Unix: export GBV_IMAGE_REGISTRY=global-build-validation
# Windows PowerShell: $env:GBV_IMAGE_REGISTRY = "global-build-validation"
nox -s run_check -- yamllint.v1
nox -s run_check -- python-validation.v1 -s black
```

## GitHub Actions (consumer repo)

After images are published:

```yaml
name: Build validation
on:
  pull_request:
jobs:
  validate:
    uses: YOUR_ORG/global-build-validation/.github/workflows/build-validation.yml@main
    with:
      image_registry: ghcr.io/YOUR_ORG/global-build-validation
```

## Azure Pipelines (consumer repo)

Create a pipeline from `azure-pipelines/pipeline.build-validation.yml` in this repository, or reference the templates:

```yaml
resources:
  repositories:
    - repository: gbv
      type: git
      name: YOUR_PROJECT/global-build-validation
      ref: main

extends:
  template: azure-pipelines/pipeline.build-validation.yml@gbv
  parameters:
    imageRegistry: YOUR_REGISTRY
    imageRepository: global-build-validation
```

By default jobs use Microsoft-hosted `ubuntu-22.04` plus `container:`. To use a self-hosted pool of checker agents set `useSelfHostedAgents: true` and `poolName`.

## Optional KEDA agents

1. Copy [helm/secrets/values.example.yaml](helm/secrets/values.example.yaml) to `helm/secrets/values.yaml` and fill in `AZP_*` plus registry credentials.
2. Install secrets, then an agent chart per image tag:

```bash
helm upgrade --install gbv-secrets helm/secrets -n global-build-validation --create-namespace -f helm/secrets/values.yaml
helm upgrade --install gbv-python helm/agent -n global-build-validation \
  --set image.repository=ghcr.io/YOUR_ORG/global-build-validation \
  --set image_tag=python-validation.v1
```

3. Point Argo CD at [gitops/agents/agents.yml](gitops/agents/agents.yml) after replacing `YOUR_GIT_URL`, `YOUR_NAMESPACE`, and `YOUR_DESTINATION_SERVER`.

Helm lint:

```bash
nox -s helm_lint
```

## Prerequisites

- Docker (to build and run checker images)
- Python 3.10+ and `nox` for local sessions
- Helm 3 (optional, for agent charts)
- A container registry you control (GHCR, ACR, Docker Hub, …)
