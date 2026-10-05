#!/usr/bin/env bash
set -euo pipefail
destination="${1:?Supply an absolute tool directory}"
[[ "$destination" == /* ]] || exit 1
case "$(uname -m)" in
  x86_64) arch=amd64 ;;
  aarch64|arm64) arch=arm64 ;;
  *) exit 1 ;;
esac
mkdir -p "$destination"
scratch="$(mktemp -d)"
cd "$scratch"
curl -fsSL -o kind "https://github.com/kubernetes-sigs/kind/releases/download/v0.33.0/kind-linux-$arch"
curl -fsSL -o kind.sha256 "https://github.com/kubernetes-sigs/kind/releases/download/v0.33.0/kind-linux-$arch.sha256sum"
expected="$(awk '{print $1}' kind.sha256)"
printf '%s  kind\n' "$expected" | sha256sum --check --status
curl -fsSL -o kubectl "https://dl.k8s.io/release/v1.35.8/bin/linux/$arch/kubectl"
curl -fsSL -o kubectl.sha256 "https://dl.k8s.io/release/v1.35.8/bin/linux/$arch/kubectl.sha256"
printf '%s  kubectl\n' "$(<kubectl.sha256)" | sha256sum --check --status
install -m 0755 kind kubectl "$destination/"
