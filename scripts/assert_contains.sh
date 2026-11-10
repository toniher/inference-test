#!/usr/bin/env bash
# Usage: assert_contains.sh <file> <regex> [--not]
# Prints the file, then checks it matches (or with --not, does not match) <regex>, case-insensitive.
set -euo pipefail
file=$1 re=$2 neg=${3:-}
echo "--- response ---"; cat "$file"; echo; echo "----------------"
[ -n "${GITHUB_STEP_SUMMARY:-}" ] && { echo "### ${GITHUB_JOB:-response}"; echo '```'; cat "$file"; echo '```'; } >> "$GITHUB_STEP_SUMMARY"
if grep -Eiq -- "$re" "$file"; then found=1; else found=0; fi
if [ "$neg" = "--not" ]; then
  [ "$found" = 0 ] || { echo "::error::unexpected match for /$re/"; exit 1; }
else
  [ "$found" = 1 ] || { echo "::error::no match for /$re/"; exit 1; }
fi
