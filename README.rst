AWS Web Stacks
==============

AWS Web Stacks is a library of CloudFormation templates for hosting web applications
on AWS using **EKS (Elastic Kubernetes Service)**. The templates create a fully-managed
hosting environment with an EKS cluster, worker nodes, S3 buckets for static assets,
an ECR repository for Docker images, and optional RDS and ElastiCache instances.
All resources are created in a self-contained VPC.

The CloudFormation templates are written in `troposphere <https://github.com/cloudtools/troposphere>`_.

Available templates:

+---------------------+-------------------+------------------+
|                     | Standard Region   | AWS GovCloud     |
+=====================+===================+==================+
| Without NAT Gateway | |EKS-No-NAT|_     | |GC-No-NAT|_     |
+---------------------+-------------------+------------------+
| With NAT Gateway    | |EKS-NAT|_        | |GC-NAT|_        |
+---------------------+-------------------+------------------+

.. |EKS-No-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _EKS-No-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=eks-app-no-nat&templateURL=https://s3.amazonaws.com/aws-web-stacks/eks-no-nat.yaml

.. |EKS-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _EKS-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=eks-app-with-nat&templateURL=https://s3.amazonaws.com/aws-web-stacks/eks-nat.yaml

.. |GC-No-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _GC-No-NAT: https://console.aws.amazon.com/us-gov-west-1/cloudformation/home?#/stacks/new?stackName=gc-eks-app-no-nat&templateURL=https://s3.amazonaws.com/aws-web-stacks/gc-no-nat.yaml

.. |GC-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _GC-NAT: https://console.aws.amazon.com/us-gov-west-1/cloudformation/home?#/stacks/new?stackName=gc-eks-app-with-nat&templateURL=https://s3.amazonaws.com/aws-web-stacks/gc-nat.yaml

NAT Gateways
------------

The templates are available with and without NAT gateways. If you select the version
without NAT gateways, instances in private subnets will not have internet access. This
is fine if your application only needs to communicate with AWS services (which are
accessed via VPC endpoints) and doesn't need to reach external APIs or package
repositories.

If your application needs outbound internet access from private subnets (e.g., to
pull Docker images, install OS packages, or call external APIs), use the version with
NAT gateways.

Stack Creation Process
----------------------

Stack creation typically takes **30-35 minutes**. The slowest resources are:

- **CloudFront distribution** (~10 min): Propagates to edge locations
- **RDS instance** (~10 min): Creates and initializes the database
- **EKS cluster** (~10 min): Provisions control plane and nodegroup

SSL Certificate
---------------

The templates automatically create an ACM certificate for your domain in ``us-east-1``
(required for CloudFront). You'll need to approve the certificate validation via email
or DNS records, depending on your domain provider.

**Note:** ``.io`` domains have known issues with ACM email validation. If you use a
``.io`` domain, you may need to create the certificate manually and pass the ARN via
the ``AssetsCloudFrontCertArn`` parameter.

Encryption
----------

The templates support three encryption modes for EBS volumes, RDS, and ElastiCache:

1. **AES-256** (default): AWS-managed keys, no additional cost
2. **Customer-managed CMK**: You provide a KMS key ARN via ``CustomerManagedCmkArn``
3. **No encryption**: Set ``UseAES256Encryption`` to ``false``

For EBS encryption on EKS nodes, you may also need to set up a key policy allowing
the EC2 service to use the key. See the `AWS EBS encryption docs
<https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/encryption-volume-creation.html>`_
for details.

Resources Created
-----------------

Each stack creates:

- **VPC**: Public and private subnets across two availability zones
- **EKS Cluster**: Managed Kubernetes control plane
- **Nodegroup**: Auto-scaling group of worker nodes
- **ECR Repository**: Docker image registry with scan-on-push
- **S3 Buckets**: Public assets bucket (with optional CloudFront) and private assets bucket
- **RDS Instance** (optional): MySQL or PostgreSQL with optional read replica
- **ElastiCache** (optional): Memcached or Redis (with optional cluster mode)
- **CloudFront** (optional): CDN for static assets with custom domain support

EKS Cluster Access
------------------

To access your EKS cluster with ``kubectl``:

.. code-block:: bash

    aws eks update-kubeconfig --name <cluster-name> --alias <alias>
    kubectl get nodes --context <alias>

For Pod Identity-enabled clusters, the EBS CSI driver uses pod identity for
authentication. After enabling ``EksUseAccessConfig=true``, you may need to
restart the EBS CSI controller:

.. code-block:: bash

    kubectl rollout restart deployment ebs-csi-driver -n kube-system

Pod Identity
------------

The v3 templates support `AWS Pod Identity <https://docs.aws.amazon.com/eks/latest/userguide/pod-identity.html>`_
for fine-grained IAM permissions to pods. This requires:

- ``EksUseAccessConfig=true``: Enables ``AccessConfig`` with ``authenticationMode: API``
- ``eks-pod-identity-agent`` add-on: Installed automatically
- IAM roles with pod identity trust policies: Created for EBS CSI driver

See "Upgrading from v2" below for full migration instructions.

Building
--------

Install dependencies (requires `uv <https://github.com/astral-sh/uv>`_):

    uv sync --locked

Build all templates:

    make templates

This generates four YAML templates in the ``content/`` directory.

Building Templates
------------------

Environment variables control which templates are generated:

- ``USE_EKS=on``: Build EKS templates (required)
- ``USE_GOVCLOUD=on``: Build GovCloud-compatible templates
- ``USE_NAT_GATEWAY=on``: Include NAT gateway in private subnets

Examples:

.. code-block:: bash

    # Standard region, no NAT
    USE_EKS=on python -c 'import stack' > content/eks-no-nat.yaml

    # Standard region, with NAT
    USE_EKS=on USE_NAT_GATEWAY=on python -c 'import stack' > content/eks-nat.yaml

    # GovCloud, with NAT
    USE_EKS=on USE_GOVCLOUD=on USE_NAT_GATEWAY=on python -c 'import stack' > content/gc-nat.yaml

Upgrading from v2 (EC2/ECS) to v3 (EKS-only)
----------------------------------------------

The v3 templates are EKS-only. Several parameters from v2 have been removed and one new
required parameter has been added. When updating an existing stack, you must adjust the
parameters accordingly.

**Parameters to remove** (no longer supported):

- ``AdministratorIPAddress``
- ``BastionAMI``
- ``BastionInstanceType``
- ``BastionKeyName``
- ``BastionType``
- ``ElasticsearchInstanceType``
- ``ElasticsearchVersion``
- ``ElasticsearchVolumeSize``
- ``UseSFTPServer``

**New required parameter:**

- ``EksUseAccessConfig``: Controls whether the EKS cluster uses the modern
  ``AccessConfig`` (``authenticationMode: API``) with Pod Identity support.

  - Set to ``false`` initially when migrating an existing cluster. This prevents
    CloudFormation from trying to replace the cluster (which fails if the cluster
    has a custom name).
  - After the stack update succeeds, manually enable API authentication:

        aws eks update-cluster-config \
          --name <cluster-name> \
          --access-config authenticationMode=API

  - Then update the stack again with ``EksUseAccessConfig=true`` to let
    CloudFormation manage the AccessConfig, Pod Identity agent, and EBS CSI driver.
  - For **new stacks**, set to ``true`` from the start.

**Notes:**

- ``AssetsBucketAccessControl`` should be set to ``Private`` when migrating existing
  stacks to avoid S3 ACL errors. New stacks can omit this (defaults to no ACL).
- After the initial update with ``EksUseAccessConfig=false``, enable API auth via CLI,
  then update again with ``EksUseAccessConfig=true``.
- The EBS CSI controller may need a restart after enabling Pod Identity:

      kubectl rollout restart deployment ebs-csi-driver -n kube-system

IPv6 / Dual-Stack Networking
----------------------------

These templates provision VPCs with dual-stack networking enabled, meaning each
subnet can use both IPv4 and IPv6 addresses:

- IPv6 support to the VPC is provided via an Amazon-provided IPv6 CIDR block added
  by setting ``AWS::EC2::VPCCidrBlock`` (``AmazonProvidedIpv6CidrBlock: true``).

  NOTE: ``AWS::EC2::VPCCidrBlock`` is used rather than trying to set IPv6 properties on the VPC resource directly,
  since CloudFormation does not support IPv6 configuration on ``AWS::EC2::VPC`` as neither
  ``AssignGeneratedIPv6CidrBlock`` nor ``IPv6CidrBlockOptions`` are valid.
- Each subnet receives a /64 IPv6 prefix via ``!Select [N, !Cidr [!Select [0, !GetAtt
  Vpc.Ipv6CidrBlocks], 4, 64]]`` (the 3rd ``Fn::Cidr`` arg is "cidrBits": 128 - 64 = 64) with ``DependsOn`` on the VPCCidrBlock.

IPv6 routing follows these conventions:

- Public subnets route all IPv6 traffic (``::/0``) through the Internet Gateway (IGW).
- Private subnets route all IPv6 traffic (``::/0``) through the Egress-Only Internet
  Gateway. The NAT gateway is only used for NAT64 traffic (``64:ff9b::/96``),
  enabling IPv6-only workloads to reach IPv4 endpoints. Services like RDS and
  ElastiCache remain IPv4-only.

  NOTE: EC2 does not allow a NAT gateway as the next hop for ``::/0``. Private
  subnets must use the Egress-Only IGW for general outbound IPv6 traffic.


Upgrading from V2 to V3: EKS IPv6 Backward Compatibility for Existing IPv4 EKS Clusters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The EKS cluster's IP family (``IPv4`` or ``IPv6``) is set at creation time and is
immutable. This means an existing IPv4 cluster cannot be modified to support IPv6.
If you need an IPv6 pod network, you would need to recreate the ``AWS::EKS::Cluster``
resource.

If IPv6 support on the cluster is not required, updating an existing IPv4-only stack (v2)
to a dual-stack template (v3) is an in-place update:

- VPC/subnets get `Modify` (IPv6 CIDR added, no replacement)
- New resources such as VPCCidrBlock, egress-only IGW, v6 routes) are `Add`


Additionally, dual-stack ingress is possible without cluster changes: the
`k8s-web-cluster <https://github.com/caktus/ansible-role-k8s-web-cluster/pull/45>`_
Ansible role can update the Traefik ingress controller to provision a dual-stack
Network Load Balancer, routing both IPv4 and IPv6 traffic to the cluster's IPv4 pods.

These changes should be applied **after** the CloudFormation stack update:

1. Set Ansible variable ``k8s_traefik_dualstack: true``.
2. Redeploy the Traefik Helm chart via the k8s-web-cluster Ansible role.
3. Traefik updates the AWS Network Load Balancer (NLB) to dual-stack.


Contributing
------------

See :doc:`CONTRIBUTING` for development setup, testing, and release process.

Copyright
---------

Copyright 2017, 2018, 2026 Jean-Phillipe Serafin, Caktus Consulting Group, LLC
