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
| Without NAT Gateway | |EKS-No-NAT|_      | |GC-No-NAT|_     |
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

Environment Variables
---------------------

Your application can access these environment variables (injected by the stack):

- ``AWS_REGION``: The AWS region
- ``AWS_STORAGE_BUCKET_NAME``: Name of the public assets S3 bucket
- ``AWS_PRIVATE_STORAGE_BUCKET_NAME``: Name of the private assets S3 bucket
- ``CDN_DOMAIN_NAME``: CloudFront distribution domain (if enabled)
- ``DATABASE_URL``: Connection string for the RDS instance (if enabled)
- ``DATABASE_HOST``: RDS hostname
- ``DATABASE_NAME``: Database name
- ``DATABASE_USER``: Database username
- ``DATABASE_PASSWORD``: Database password
- ``CACHE_URL``: Connection string for ElastiCache (if enabled)
- ``CACHE_HOST``: ElastiCache hostname
- ``CACHE_PORT``: ElastiCache port

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

For existing clusters, migrate in three steps:

1. Update stack with ``EksUseAccessConfig=false``
2. Enable API auth via CLI: ``aws eks update-cluster-config --name <cluster> --access-config authenticationMode=API``
3. Update stack with ``EksUseAccessConfig=true``

See :doc:`README` "Upgrading from v2" section for full migration instructions.

Building
--------

Install dependencies (requires `uv <https://github.com/astral-sh/uv>`_):

    uv sync --locked

Build all templates:

    make templates

This generates four YAML templates in the ``content/`` directory.

Parameters
----------

Key parameters include:

- **DomainName**: Your application's domain name
- **EksClusterName**: Name for the EKS cluster
- **EksClusterVersion**: Kubernetes version (optional)
- **EksUseAccessConfig**: Enable API authentication mode and Pod Identity (required)
- **ContainerInstanceType**: EC2 instance type for worker nodes
- **ContainerVolumeSize**: EBS volume size for worker nodes (GB)
- **DatabaseClass**: RDS instance class (or "(none)" to skip)
- **DatabaseEngine**: RDS engine (``mysql`` or ``postgres``)
- **DatabaseEngineVersion**: Engine version (e.g., ``8.4`` for MySQL)
- **CacheNodeType**: Memcached node type (or "(none)" to skip)
- **RedisNodeType**: Redis node type (or "(none)" to skip)
- **DesiredScale**: Desired number of worker nodes
- **MaxScale**: Maximum number of worker nodes
- **VpcCidr**: VPC CIDR block
- **UseAES256Encryption**: Enable AES-256 encryption (default: true)
- **CustomerManagedCmkArn**: KMS key ARN for customer-managed encryption
- **EnableEksEncryptionConfig**: Enable EKS control plane encryption
- **EksPublicAccessCidrs**: CIDR blocks allowed to access the public API endpoint

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

Contributing
------------

See :doc:`CONTRIBUTING` for development setup, testing, and release process.

Copyright
---------

Copyright 2017, 2018 Jean-Phillipe Serafin, Tobias McNulty
