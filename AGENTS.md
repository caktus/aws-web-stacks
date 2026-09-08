# AGENTS.md - Development Instructions for aws-web-stacks

## Overview

This repository generates CloudFormation templates for EKS-only deployments.
All templates must stay under **51,200 bytes** to fit within CloudFormation's
template size limits when combined with other stacks.

## Prerequisites

### 1. Verify AWS Sandbox Access (FIRST STEP)

Sandbox setup is documented in :doc:`sandbox/README`. In short:

```bash
source ~/.sandbox-aws-env
.venv/bin/aws sts get-caller-identity
```

Expected output: account `148142827518`, role `SandboxAdminRole`, region `us-east-1`.

If this fails, stop and ask the user for credentials.

### 2. Python Virtual Environment

The project uses a Python virtual environment at `.venv/`, managed by `uv`. AWS CLI
is located at `.venv/bin/aws` (not in system PATH). Dependencies are defined in
`pyproject.toml`.

```bash
# Install or update dependencies
uv sync
```

To add or remove a dependency, edit `pyproject.toml` and run `uv sync` again.

## Building Templates

### Quick Build

```bash
USE_EKS=on .venv/bin/python -c 'import stack' > content/eks-no-nat.yaml
USE_EKS=on USE_NAT_GATEWAY=on .venv/bin/python -c 'import stack' > content/eks-nat.yaml
USE_EKS=on USE_GOVCLOUD=on .venv/bin/python -c 'import stack' > content/gc-no-nat.yaml
USE_EKS=on USE_GOVCLOUD=on USE_NAT_GATEWAY=on .venv/bin/python -c 'import stack' > content/gc-nat.yaml
```

### Using Makefile

```bash
make clean
make templates
```

This builds all 4 templates: `eks-no-nat.yaml`, `eks-nat.yaml`, `gc-no-nat.yaml`, `gc-nat.yaml`.

### Size Verification

All templates must be under 51,200 bytes:

```bash
ls -la content/*.yaml
```

## Architecture

### Stack Modules (`stack/`)

| Module | Purpose |
|--------|---------|
| `__init__.py` | Entry point - imports all modules, conditional on `USE_EKS`/`USE_GOVCLOUD`/`USE_NAT_GATEWAY` |
| `common.py` | Shared parameters (encryption, KMS), `arn_prefix` for GovCloud compatibility |
| `template.py` | Base `InterfaceTemplate` class with parameter groups |
| `vpc.py` | VPC, subnets, internet gateway, NAT gateway (conditional) |
| `security_groups.py` | Container security group with EKS cluster tagging |
| `eks.py` | EKS cluster, nodegroup, launch template, EBS CSI + Pod Identity add-ons |
| `containers.py` | EKS node instance type, volume size, IAM role/policies |
| `database.py` | RDS instance (mysql/postgres), optional replica, encryption |
| `cache.py` | Memcached (CacheCluster) and Redis (ReplicationGroup), encryption |
| `assets.py` | S3 buckets (public + private), CloudFront distribution for static assets |
| `domain.py` | Domain name parameters, ACM certificate for app domain |
| `logs.py` | CloudWatch logging policy (uses `arn_prefix` for GovCloud) |
| `repository.py` | ECR repository (uses `arn_prefix` for GovCloud) |
| `tags.py` | Stack name tag applied to all resources |
| `utils.py` | `ParameterWithDefaults` class for default overrides |
| `constants.py` | Shared constants like `dont_create_value = "(none)"` |

### Key Design Decisions

1. **EKS-only**: All other deployment modes (EC2, ECS, Elastic Beanstalk, Dokku) were removed.
2. **GovCloud uses EKS**: No special EC2 handling for GovCloud - it uses the same EKS stack.
3. **No AllowedValues for instance types**: Users specify instance types directly as strings.
   This avoids needing to update templates when new instance types are released.
4. **`arn_prefix` for GovCloud**: All managed policy ARNs use `Join("", [arn_prefix, ":iam::aws:policy/..."])`
   to automatically use `arn:aws-us-gov` in GovCloud regions.
5. **Encryption preserved**: All encryption parameters (AES-256, KMS) are retained across database,
   cache, and assets modules.

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `USE_EKS` | Must be set to `on` for all builds |
| `USE_GOVCLOUD` | Set to `on` for GovCloud templates (changes `arn_prefix`) |
| `USE_NAT_GATEWAY` | Set to `on` to include NAT gateway in private subnets |

## Testing

### Sandbox Deployment

**IMPORTANT: Use changesets for iterative testing.** Dropping and recreating the cluster
each iteration wastes ~15 minutes. Create the stack once, then use `update-stack` with
the rebuilt template for subsequent iterations. Only do a full delete/recreate at the very
end to verify a clean deployment works.

**Use `t3.medium` or larger for sandbox nodes.** The default `t3a.micro` (1 vCPU, 1 GB)
cannot fit the EBS CSI controller, CoreDNS, VPC CNI, kube-proxy, and pod identity agent
simultaneously — you'll get "Too many pods" scheduling failures. Use `t3.medium` (2 vCPU,
4 GB) or larger to avoid this.

For sandbox setup (role deployment, credentials), see ``sandbox/readme.md``.

#### Initial stack creation

```bash
source ~/.sandbox-aws-env
export AWS_DEFAULT_REGION=us-east-1

.venv/bin/aws cloudformation create-stack \
  --stack-name pi-sandbox-test \
  --template-body file://content/eks-no-nat.yaml \
  --parameters \
    ParameterKey=DomainName,ParameterValue=example.com \
    ParameterKey=DomainNameAlternates,ParameterValue= \
    ParameterKey=DatabasePassword,ParameterValue=T3stP4ssw0rd1 \
    ParameterKey=DatabaseParameterGroupFamily,ParameterValue= \
    ParameterKey=EksClusterName,ParameterValue=pi-sandbox-test \
    ParameterKey=EksClusterVersion,ParameterValue=1.35 \
    ParameterKey=EksUseAccessConfig,ParameterValue=true \
    ParameterKey=PrimaryAZ,ParameterValue=us-east-1a \
    ParameterKey=SecondaryAZ,ParameterValue=us-east-1b \
    ParameterKey=ContainerInstanceType,ParameterValue=t3.medium \
    ParameterKey=ContainerVolumeSize,ParameterValue=30 \
    ParameterKey=DatabaseClass,ParameterValue="(none)" \
    ParameterKey=CacheNodeType,ParameterValue="(none)" \
    ParameterKey=RedisNodeType,ParameterValue="(none)" \
    ParameterKey=AssetsCloudFrontDomain,ParameterValue= \
    ParameterKey=AssetsCloudFrontCertArn,ParameterValue= \
    ParameterKey=UseAES256Encryption,ParameterValue=true \
    ParameterKey=CustomerManagedCmkArn,ParameterValue= \
    ParameterKey=EnableEksEncryptionConfig,ParameterValue=false \
    ParameterKey=EksPublicAccessCidrs,ParameterValue= \
    ParameterKey=VpcCidr,ParameterValue=10.0.0.0/16 \
    ParameterKey=PublicSubnetACidr,ParameterValue=10.0.0.0/20 \
    ParameterKey=PublicSubnetBCidr,ParameterValue=10.0.16.0/20 \
    ParameterKey=PrivateSubnetACidr,ParameterValue=10.0.32.0/20 \
    ParameterKey=PrivateSubnetBCidr,ParameterValue=10.0.48.0/20 \
    ParameterKey=CustomAMIImageType,ParameterValue= \
    ParameterKey=CustomEKSAMI,ParameterValue= \
    ParameterKey=DesiredScale,ParameterValue=2 \
    ParameterKey=MaxScale,ParameterValue=4 \
  --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND
```

#### Iterative updates (after initial creation)

```bash
# Rebuild template, then update in-place
USE_EKS=on .venv/bin/python -c 'import stack' > content/eks-no-nat.yaml

.venv/bin/aws cloudformation update-stack \
  --stack-name pi-sandbox-test \
  --template-body file://content/eks-no-nat.yaml \
  --parameters \
    ParameterKey=DomainName,ParameterValue=example.com \
    ParameterKey=DomainNameAlternates,ParameterValue= \
    ParameterKey=DatabasePassword,ParameterValue=T3stP4ssw0rd1 \
    ParameterKey=DatabaseParameterGroupFamily,ParameterValue= \
    ParameterKey=EksClusterName,ParameterValue=pi-sandbox-test \
    ParameterKey=EksClusterVersion,ParameterValue=1.35 \
    ParameterKey=EksUseAccessConfig,ParameterValue=true \
    ParameterKey=PrimaryAZ,ParameterValue=us-east-1a \
    ParameterKey=SecondaryAZ,ParameterValue=us-east-1b \
    ParameterKey=ContainerInstanceType,ParameterValue=t3.medium \
    ParameterKey=ContainerVolumeSize,ParameterValue=30 \
    ParameterKey=DatabaseClass,ParameterValue="(none)" \
    ParameterKey=CacheNodeType,ParameterValue="(none)" \
    ParameterKey=RedisNodeType,ParameterValue="(none)" \
    ParameterKey=AssetsCloudFrontDomain,ParameterValue= \
    ParameterKey=AssetsCloudFrontCertArn,ParameterValue= \
    ParameterKey=UseAES256Encryption,ParameterValue=true \
    ParameterKey=CustomerManagedCmkArn,ParameterValue= \
    ParameterKey=EnableEksEncryptionConfig,ParameterValue=false \
    ParameterKey=EksPublicAccessCidrs,ParameterValue= \
    ParameterKey=VpcCidr,ParameterValue=10.0.0.0/16 \
    ParameterKey=PublicSubnetACidr,ParameterValue=10.0.0.0/20 \
    ParameterKey=PublicSubnetBCidr,ParameterValue=10.0.16.0/20 \
    ParameterKey=PrivateSubnetACidr,ParameterValue=10.0.32.0/20 \
    ParameterKey=PrivateSubnetBCidr,ParameterValue=10.0.48.0/20 \
    ParameterKey=CustomAMIImageType,ParameterValue= \
    ParameterKey=CustomEKSAMI,ParameterValue= \
    ParameterKey=DesiredScale,ParameterValue=2 \
    ParameterKey=MaxScale,ParameterValue=4 \
  --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND
```

#### Final clean verification

Once all iterations are done, delete and recreate from scratch to confirm a clean deploy:

```bash
.venv/bin/aws cloudformation delete-stack --stack-name pi-sandbox-test
# Wait for DELETE_COMPLETE, then run the initial create-stack command above
```

### kubectl Access

```bash
source ~/.sandbox-aws-env
export AWS_DEFAULT_REGION=us-east-1
export PATH="/home/tobias/aws-web-stacks/.venv/bin:$PATH"

.venv/bin/aws eks update-kubeconfig --name <cluster-name> --alias <alias>
kubectl get nodes --context <alias>
```

### IPv6 / Dualstack

- VPCs are always dualstack: an Amazon-provided IPv6 CIDR block is added via
  `AWS::EC2::VPCCidrBlock` (`AmazonProvidedIpv6CidrBlock: true`). Subnets take
  their /64s via `!Select [N, !Cidr [!Select [0, !GetAtt Vpc.Ipv6CidrBlocks], 4, 64]]`
  (the 3rd `Fn::Cidr` arg is "cidrBits": 128 - 64 = 64) with `DependsOn` on the
  VPCCidrBlock. Routes: public subnets `::/0` -> IGW; private subnets `::/0` ->
  egress-only IGW and `64:ff9b::/96` -> NAT gateway (NAT64 for IPv6-only
  workloads). Other services (RDS, ElastiCache) stay IPv4-only.
- **A NAT gateway cannot be the next hop for `::/0`** (EC2 rejects it: only
  `64:ff9b::/96` may point at a NAT gateway). Use the egress-only IGW for
  outbound IPv6 from private subnets.
- **`AWS::EC2::VPC` has no IPv6 properties in CloudFormation** — neither
  `AssignGeneratedIpv6CidrBlock` nor `Ipv6CidrBlockOptions` are valid
  (cfn-lint and CFN early validation both reject them). Use the separate
  `AWS::EC2::VPCCidrBlock` resource.
- **Backwards compatible**: updating an existing IPv4-only stack to a dualstack
  template is in-place — VPC/subnets get `Modify` (IPv6 CIDR added, no
  replacement), new resources (VPCCidrBlock, egress-only IGW, v6 routes) are
  `Add`. Verified in the sandbox (see `pi-sandbox-ipv4-legacy` test).
- **EKS IP family is immutable**: `AWS::EC2::Cluster` supports setting
  `IpFamily` (`ipv4` or `ipv6`) at **creation time** only.
  This means `ipFamily` **cannot** be changed post-creation. Converting an
  existing IPv4 EKS cluster's internal pod network to IPv6 requires
  recreating the `AWS::EKS::Cluster` resource.
- **Dual Stack Ingress via Traefik (No Cluster Recreation)**: Even if an existing EKS cluster
  remains `ipv4` only internally, its public ingress load balancer can be converted to dual-stack in place.
  This can be handled by the [k8s-web-cluster](https://github.com/caktus/ansible-role-k8s-web-cluster/pull/45)
  Ansible role deployed **after** applying CloudFormation stack changes:
  1. Set Ansible variable `k8s_traefik_dualstack: true`.
  2. Redeploy the Traefik Helm chart via k8s-web-cluster Ansible role.
  3. Traefik updates the AWS Network Load Balancer (NLB) annotations to route incoming IPv6 and IPv4 public traffic to the internal IPv4 EKS pods.


### EKS Add-on Health

Use `addon.` prefix in query paths (not bare property names):

```bash
# Check addon status and health
.venv/bin/aws eks describe-addon \
  --cluster-name <cluster-name> \
  --addon-name <addon-name> \
  --query '{Status:addon.status, Health:addon.health}'

# List all addons
.venv/bin/aws eks list-addons --cluster-name <cluster-name>
```

Common statuses: `ACTIVE`, `DEGRADED`, `CREATE_IN_PROGRESS`, `DELETE_IN_PROGRESS`.
DEGRADED addons have `health.issues` with codes like `InsufficientNumberOfReplicas`.

### Pod Identity

- Requires EKS cluster with `authenticationMode: API` (set in `AccessConfig`)
- Requires `eks-pod-identity-agent` add-on installed before associations can be created
- **Trust policy must use `StringEquals` with a manually-constructed cluster ARN via `Join`** —
  `GetAtt(cluster, "Arn")` is unreliable in IAM trust policy documents and will cause
  `PodIdentityAssociation` to fail with "Trust policy of the role provided is invalid"
- Trust policy principal: `pods.eks.amazonaws.com` with actions `sts:AssumeRole` + `sts:TagSession`
- Condition: `StringEquals` on `aws:SourceArn` = `Join("", [arn_prefix, ":eks:", Ref(AWS_REGION), ":", Ref(AWS_ACCOUNT_ID), ":cluster/", cluster_name])`
- `PodIdentityAssociation` must have `DependsOn` on **both** `PodIdentityAddon` and `EBSCSIAddon`
- Sandboxes **do** support Pod Identity (verified in account `148142827518`)

### Cleanup

```bash
.venv/bin/aws cloudformation delete-stack --stack-name pi-sandbox-test
```

### Sandbox Pitfalls

#### Node sizing

- Default `t3a.micro` (1 vCPU, 1 GB) cannot fit all system pods (EBS CSI controller,
  CoreDNS, VPC CNI, kube-proxy, pod identity agent). Use `t3.medium` or larger.
- "Too many pods" / "InsufficientNumberOfReplicas" errors on addons are almost always
  a node sizing issue, not a template bug.

#### Pod Identity trust policy

- `GetAtt(cluster, "Arn")` in IAM trust policies may not resolve correctly — always
  construct the ARN manually with `Join` using `arn_prefix`, `AWS_REGION`, `AWS_ACCOUNT_ID`,
  and the cluster name parameter.
- Use `StringEquals` (not `ArnEquals`) for the `aws:SourceArn` condition.
- The `PodIdentityAssociation` resource needs `DependsOn` on both the pod identity agent
  addon AND the EBS CSI addon (e.g., `DependsOn=["PodIdentityAddon", "EBSCSIAddon"]`).
- Addons don't need `DependsOn` on the cluster — `ClusterName=Ref(cluster)` already
  enforces the dependency (cfn-lint W3005 warns about redundant DependsOn).
- **Race condition**: The EBS CSI controller pods may start before the pod identity agent
  is ready to serve the association, causing CrashLoopBackOff with "not authorized" errors.
  The fix is to restart the controller deployment after the stack is created:
  `kubectl rollout restart deployment ebs-csi-controller -n kube-system`.
  This is a known limitation of the CloudFormation approach — the agent and controller
  are managed by EKS, not CloudFormation, so CloudFormation can't enforce ordering.

#### Iterative testing

- **Never drop and recreate the cluster for each iteration** — it takes ~15 minutes.
- Use `cloudformation update-stack` with the rebuilt template for iterative changes.
- Only do a full delete/recreate at the very end to verify clean deployment.

## Common Pitfalls

### Troposphere 4.2.0 Limitations

- `In()` intrinsic function does not exist - use `Or(Equals(...), Equals(...))` instead
- `AllowedMethods`, `CachedMethods`, `Compress`, `Origins` are properties on `DefaultCacheBehavior`, not separate imports
- `OriginAccessControlSigningProtocol` does not exist in cloudfront module
- `TagSpecifications` (plural) is the correct class name, `ResourceType` is a plain string (e.g., "instance")
- `Origin` requires `Id` attribute, and `S3Origin` is not directly usable in `Origins` list

### GovCloud Compatibility

- Sandbox credentials work only in `us-east-1`, not GovCloud regions
- All ARN prefixes must use `arn_prefix` from `common.py` (resolves to `arn:aws` or `arn:aws-us-gov`)
- `in_govcloud_region` checks for both `us-gov-west-1` and `us-gov-east-1`

### Template Size

- If a build exceeds 51,200 bytes, reduce by: removing AllowedValues lists, simplifying descriptions,
  removing optional features, or consolidating parameters
- Check sizes with: `wc -c content/*.yaml`

## CI/CD

- `pre-commit.yaml`: Runs pre-commit hooks on PR/push
- `release.yaml`: On tag push, builds versioned templates, uploads to S3 and GitHub release
