#!/usr/bin/env bash
set -euo pipefail

if git grep -nEI -e "(api[_-]?key|secret|token|password)[[:space:]]*[:=][[:space:]]*['\"][A-Za-z0-9_./+-]{20,}" -- ':!scripts/check-secrets.sh'; then
  echo "Possible committed secret found." >&2
  exit 1
fi

if git grep -nE -e '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'; then
  echo "Committed private key found." >&2
  exit 1
fi

echo "No obvious committed secrets found."
