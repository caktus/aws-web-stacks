#!/usr/bin/env bash
#
# sandbox-creds.sh — mint temporary credentials for the sandbox account.
#
# Runs on your PRIMARY workstation (which has long-lived creds or SSO).
# Calls sts:AssumeRole against the sandbox SandboxAdminRole and prints
# short-lived credentials you can copy/paste or pipe to your dev VM.
#
# Usage:
#   ./sandbox-creds.sh --role-arn arn:aws:iam::222222222222:role/SandboxAdminRole \
#                      --external-id sandbox-testing \
#                      --duration 1h \
#                      --format env        # env | json | profile | remote
#
# Durations: 15m .. 12h (STS single-session cap). For "day" or "week"
# access, hand the dev VM a named profile (--format profile) that re-assumes
# on demand, so each underlying credential is still short-lived.

set -euo pipefail

ROLE_ARN=""
EXTERNAL_ID="sandbox-testing"
DURATION="1h"
FORMAT="env"
SESSION_NAME="sandbox-$(date +%s)"
REMOTE_HOST=""

die() { echo "error: $*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --role-arn)     ROLE_ARN="$2"; shift 2;;
    --external-id)  EXTERNAL_ID="$2"; shift 2;;
    --duration)     DURATION="$2"; shift 2;;
    --format)       FORMAT="$2"; shift 2;;
    --session-name) SESSION_NAME="$2"; shift 2;;
    --remote-host)  REMOTE_HOST="$2"; shift 2;;
    -h|--help)      grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) die "unknown arg: $1";;
  esac
done

[[ -n "$ROLE_ARN" ]] || die "--role-arn is required"
command -v aws >/dev/null || die "aws CLI not found"
command -v jq  >/dev/null || die "jq not found"

# Convert 15m / 2h / etc to seconds; clamp to STS 1h..12h window.
to_seconds() {
  local d="$1" n unit
  n="${d%[mh]}"; unit="${d: -1}"
  case "$unit" in
    m) echo $(( n * 60 ));;
    h) echo $(( n * 3600 ));;
    *) echo "$d";;  # assume raw seconds
  esac
}
SECONDS_DUR=$(to_seconds "$DURATION")
(( SECONDS_DUR >= 900 ))   || die "duration must be >= 15m"
(( SECONDS_DUR <= 43200 )) || die "duration must be <= 12h (STS cap)"

CREDS_JSON=$(aws sts assume-role \
  --role-arn "$ROLE_ARN" \
  --role-session-name "$SESSION_NAME" \
  --external-id "$EXTERNAL_ID" \
  --duration-seconds "$SECONDS_DUR" \
  --output json)

AK=$(echo "$CREDS_JSON" | jq -r '.Credentials.AccessKeyId')
SK=$(echo "$CREDS_JSON" | jq -r '.Credentials.SecretAccessKey')
ST=$(echo "$CREDS_JSON" | jq -r '.Credentials.SessionToken')
EXP=$(echo "$CREDS_JSON" | jq -r '.Credentials.Expiration')

emit_env() {
  cat <<EOF
# expires: $EXP
export AWS_ACCESS_KEY_ID=$AK
export AWS_SECRET_ACCESS_KEY=$SK
export AWS_SESSION_TOKEN=$ST
EOF
}

case "$FORMAT" in
  env)  emit_env;;
  json) echo "$CREDS_JSON" | jq '.Credentials';;
  profile)
    aws configure set aws_access_key_id     "$AK" --profile sandbox
    aws configure set aws_secret_access_key "$SK" --profile sandbox
    aws configure set aws_session_token     "$ST" --profile sandbox
    echo "Wrote profile 'sandbox' (expires $EXP). Use: aws --profile sandbox ..." >&2
    ;;
  remote)
    [[ -n "$REMOTE_HOST" ]] || die "--remote-host required for remote format"
    emit_env | ssh "$REMOTE_HOST" 'cat >> ~/.sandbox-aws-env && echo "credentials installed on $(hostname); source ~/.sandbox-aws-env"'
    ;;
  *) die "unknown format: $FORMAT";;
esac
