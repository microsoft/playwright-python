#!/usr/bin/env bash
set -e
set +x

if [[ ($1 == '--help') || ($1 == '-h') ]]; then
  echo "usage: $(basename $0)"
  echo
  echo "Test check_layers.js with small images that this script builds."
  echo
  exit 0
fi

# The images that we publish are clean, so a build never sees check_layers.js fail.
# This test gives it an image with forbidden files, to know that it still finds them.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
TMP_DIR="$(mktemp -d)"

function cleanup() {
  rm -rf "${TMP_DIR}"
  docker rmi -f playwright:check-layers-bad playwright:check-layers-good \
      playwright:check-layers-child playwright:check-layers-base > /dev/null 2>&1 || true
}
trap cleanup EXIT

cd "${TMP_DIR}"
echo "placeholder" > file
touch empty

# 1. Forbidden files in a lower layer must fail the check.
FORBIDDEN_FILES=(
  root/.npmrc
  certs/server.key
  home/pwuser/id_ed25519
  root/.cache/pip/http-v2/a/b/c
  etc/pip.conf
  root/.m2/settings.xml
  root/.dotnet/TelemetryStorageService/a.trn
  root/.nuget/NuGet/NuGet.Config
)
echo "FROM scratch" > Dockerfile.bad
for FORBIDDEN_FILE in "${FORBIDDEN_FILES[@]}"; do
  echo "COPY file /${FORBIDDEN_FILE}" >> Dockerfile.bad
done
echo "COPY file /readme" >> Dockerfile.bad
docker build -q -t playwright:check-layers-bad -f Dockerfile.bad . > /dev/null
if node "${SCRIPT_DIR}/check_layers.js" playwright:check-layers-bad > output.txt 2>&1; then
  cat output.txt
  echo "FAILED: check_layers.js passed for an image with forbidden files in its layers"
  exit 1
fi
# The check must fail because it found the files, not because it crashed.
for FORBIDDEN_FILE in "${FORBIDDEN_FILES[@]}"; do
  if ! grep -q -x -F "  ${FORBIDDEN_FILE}" output.txt; then
    cat output.txt
    echo "FAILED: check_layers.js did not report ${FORBIDDEN_FILE}"
    exit 1
  fi
done

# 2. An image with only allowed files must pass the check. An empty file is
#    allowed too: BuildKit can leave one at the target of a secret mount.
cat > Dockerfile.good <<'DOCKERFILE'
FROM scratch
COPY file /usr/local/lib/node_modules/npm/.npmrc
COPY file /etc/ssl/certs/ca.pem
COPY file /home/pwuser/.ssh-notes/id_ed25519.pub
COPY empty /root/.npmrc
COPY empty /etc/pip.conf
COPY file /readme
DOCKERFILE
docker build -q -t playwright:check-layers-good -f Dockerfile.good . > /dev/null
if ! node "${SCRIPT_DIR}/check_layers.js" playwright:check-layers-good > output.txt 2>&1; then
  cat output.txt
  echo "FAILED: check_layers.js failed for an image with no forbidden files"
  exit 1
fi

# 3. With --base-image, forbidden files in the base image pass, and forbidden
#    files in our layers still fail.
cat > Dockerfile.base <<'DOCKERFILE'
FROM scratch
COPY file /root/.dotnet/sentinel
DOCKERFILE
docker build -q -t playwright:check-layers-base -f Dockerfile.base . > /dev/null
cat > Dockerfile.child <<'DOCKERFILE'
FROM playwright:check-layers-base
COPY file /readme
DOCKERFILE
docker build -q -t playwright:check-layers-child -f Dockerfile.child . > /dev/null
if node "${SCRIPT_DIR}/check_layers.js" playwright:check-layers-child > output.txt 2>&1; then
  cat output.txt
  echo "FAILED: check_layers.js passed for a forbidden file in the base image, without --base-image"
  exit 1
fi
if ! node "${SCRIPT_DIR}/check_layers.js" --base-image=playwright:check-layers-base playwright:check-layers-child > output.txt 2>&1; then
  cat output.txt
  echo "FAILED: check_layers.js failed for a forbidden file in the base image, with --base-image"
  exit 1
fi
cat > Dockerfile.child <<'DOCKERFILE'
FROM playwright:check-layers-base
COPY file /root/.dotnet/other
DOCKERFILE
docker build -q -t playwright:check-layers-child -f Dockerfile.child . > /dev/null
if node "${SCRIPT_DIR}/check_layers.js" --base-image=playwright:check-layers-base playwright:check-layers-child > output.txt 2>&1; then
  cat output.txt
  echo "FAILED: check_layers.js passed for a forbidden file in our layer, with --base-image"
  exit 1
fi

echo "PASSED: check_layers.js finds forbidden files and accepts clean images"
