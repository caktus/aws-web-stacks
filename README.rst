AWS Web Stacks
==============

AWS Web Stacks is a library of CloudFormation templates for hosting web applications
on AWS using **EKS (Elastic Kubernetes Service)**. The templates create a fully-managed
hosting environment with an EKS cluster, worker nodes, S3 buckets for static assets,
an ECR repository for Docker images, and optional RDS, ElastiCache, and Elasticsearch
instances. All resources are created in a self-contained VPC.

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
- **ContainerInstanceType**: EC2 instance type for worker nodes
- **DatabaseClass**: RDS instance class (or "(none)" to skip)
- **CacheNodeType**: ElastiCache node type (or "(none)" to skip)
- **RedisNodeType**: Redis node type (or "(none)" to skip)
- **ElasticsearchInstanceType**: ES instance type (or "(none)" to skip; not available in GovCloud)

Upgrading from v2 to v3 (EKS-only)
----------------------------------

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

  - Set to ``false`` when migrating an existing cluster. This prevents
    CloudFormation from trying to replace the cluster (which fails if the cluster
    has a custom name).
  - For **new stacks**, set to ``true`` from the start.

- ``AssetsBucketAccessControl`` should be set to the existing value when migrating existing
  stacks to avoid S3 ACL errors. New stacks can omit this (defaults to no ACL).
