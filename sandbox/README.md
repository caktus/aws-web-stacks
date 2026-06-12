# Disposable AWS Sandbox Toolkit

Temporary, automated access to an isolated AWS sandbox for CloudFormation
testing.

## Why not "create a temp account"?

AWS account *creation* and *closure* can't be cleanly automated, and a closed
account lingers (and can still incur trailing charges) for ~90 days. The
robust pattern is **one persistent sandbox account you reset**, accessed via
**short-lived STS credentials**, and emptied with **aws-nuke**.

```
Primary workstation (long-lived creds / SSO)
        │  sts:AssumeRole (15min–12h)
        ▼
Sandbox account 222222222222
   ├─ SandboxAdminRole   ← assumed for temporary access
   ├─ Budget guardrail   ← email alert on forecast overspend
   └─ everything else     ← wiped by aws-nuke on schedule
```

## Hour / day / week access

A single STS session is capped at **12 hours** by AWS. So:

- **≤12h (hour/day-ish):** `sandbox-creds.sh --duration 12h --format env` →
  copy/paste the exports, or `--format remote --remote-host devvm` to push
  them onto the dev VM over SSH.
- **Day/week:** hand the dev VM the `sandbox` *profile*
  (`--format profile`). Each command re-assumes the role and gets a fresh
  short-lived credential, so access spans a week while no single credential
  outlives 12h. Revoke any time by deleting/retagging the role.

## Files

| File | Purpose |
|------|---------|
| `sandbox-access-role.yaml` | CFN: cross-account role + budget. Deploy once. |
| `bootstrap.sh` | Deploys the stack into the sandbox account. |
| `sandbox-creds.sh` | Mints temporary STS creds (env/json/profile/remote). |

## Prerequisites

- `aws` CLI v2
- `jq`

## Setup

1. **Deploy the role** (run with sandbox-account creds):
   ```bash
   ./bootstrap.sh --trusted-arn arn:aws:iam::111111111111:user/me \
                  --alert-email me@example.com --budget 20
   ```
2. **Get temporary creds** (run on your workstation):
   ```bash
   $ AWS_PROFILE=my-admin-profile sh ./sandbox-creds.sh \
     --role-arn arn:aws:iam::111111111111:role/SandboxAdminRole \
     --duration 12h \
     --format remote \
     --remote-host devvm
   ```
3. **Test your CloudFormation stack** in the sandbox as usual.
