#!/usr/bin/env bash
#
# bootstrap.sh — deploy the sandbox access role + budget guardrail (run ONCE).
#
# Run with credentials for the SANDBOX account (e.g. its root/bootstrap user
# or an SSO session into it).
#
# Usage:
#   ./bootstrap.sh \
#     --trusted-arn arn:aws:iam::111111111111:user/me \
#     --alert-email me@example.com \
#     [--external-id sandbox-testing] [--budget 20] [--profile sandbox-boot]

set -euo pipefail

TRUSTED_ARN="" ; ALERT_EMAIL="" ; EXTERNAL_ID="sandbox-testing"
BUDGET="20" ; PROFILE="" ; STACK="sandbox-access"
TEMPLATE="$(dirname "$0")/sandbox-access-role.yaml"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --trusted-arn) TRUSTED_ARN="$2"; shift 2;;
    --alert-email) ALERT_EMAIL="$2"; shift 2;;
    --external-id) EXTERNAL_ID="$2"; shift 2;;
    --budget)      BUDGET="$2"; shift 2;;
    --profile)     PROFILE="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 1;;
  esac
done

[[ -n "$TRUSTED_ARN" ]] || { echo "--trusted-arn required" >&2; exit 1; }
[[ -n "$ALERT_EMAIL" ]] || { echo "--alert-email required" >&2; exit 1; }

PROFILE_ARG=()
[[ -n "$PROFILE" ]] && PROFILE_ARG=(--profile "$PROFILE")

aws cloudformation deploy \
  --stack-name "$STACK" \
  --template-file "$TEMPLATE" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    TrustedPrincipalArn="$TRUSTED_ARN" \
    BudgetAlertEmail="$ALERT_EMAIL" \
    ExternalId="$EXTERNAL_ID" \
    MonthlyBudgetUSD="$BUDGET" \
  "${PROFILE_ARG[@]}"

echo
echo "Deployed. Role ARN:"
aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='RoleArn'].OutputValue" \
  --output text "${PROFILE_ARG[@]}"
