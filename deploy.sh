#!/bin/bash

set -xe

# shellcheck source=/dev/null
source /root/check.sh

REPO_URL="https://github.com/GDP-ADMIN/${PROJECT}.git"
BRANCH="${BRANCH_NAME}"
CLONE_DIR="/home/deployer/${PROJECT}"

echo "Setup git authentication"
ssh deployer@"${TELEPORT_HOSTNAME}" <<EOF
  git config --unset credential.helper
  git config --global user.username infra-gl
  git config --global user.email infra@gdplabs.id
  git config --global url."https://${GH_TOKEN}:x-oauth-basic@github.com/".insteadOf "https://github.com/"
  git config --global url."https://${GH_TOKEN}:x-oauth-basic@github.com".insteadOf "ssh://git@github.com"

  # Clone repo if not already present
  if [ ! -d "${CLONE_DIR}" ]; then
    git clone --branch "${BRANCH}" "${REPO_URL}" "${CLONE_DIR}"
    cd "${CLONE_DIR}"
    source env/bin/activate
    ./install.sh
    python swirl.py stop
    python swirl.py start
  else
    cd "${CLONE_DIR}"
    git fetch origin
    git checkout "${BRANCH}"
    git pull origin "${BRANCH}"
    source env/bin/activate
    ./install.sh
    python swirl.py stop
    python swirl.py start
  fi

  exit 0

EOF

