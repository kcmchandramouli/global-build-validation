#!/usr/bin/env bash
# Run a checker image against the current directory (Unix).
# Cross-platform equivalent: nox -s run_check -- <image-tag> [entrypoint-args...]
# Usage: scripts/run-image.sh <image-tag> [entrypoint-args...]
# Example: scripts/run-image.sh yamllint.v1

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${1:?image tag is required (see images/catalog.yml)}"
shift || true

REGISTRY="${GBV_IMAGE_REGISTRY:-global-build-validation}"
IMAGE="${REGISTRY}:${TAG}"

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Image $IMAGE not found locally. Build it with: nox -s build_image -- ${TAG}" >&2
  exit 1
fi

docker run --rm \
  -e ERROR_AS_WARNING="${ERROR_AS_WARNING:-false}" \
  -e BRANCH_TO_CHECK="${BRANCH_TO_CHECK:-}" \
  -e TF_BUILD="${TF_BUILD:-}" \
  -v "${ROOT}:/workspace" \
  -w /workspace \
  --entrypoint /usr/local/bin/docker_entrypoint.sh \
  "$IMAGE" \
  "$@"
