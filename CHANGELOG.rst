Change Log
==========

`X.Y.Z`_ (TBD-DD-DD)
---------------------


`2.3.0`_ (2024-11-21)
---------------------

* Add support for CloudFront Distribution in front of the application server via a separate CloudFormation stack (must be deployed on its own, after the main stack creation)


`2.2.0`_ (2024-08-01)
---------------------

* Add support for T4g instance types. (#114)
* Add support for PostgreSQL 13 and 14 RDS parameter groups. (#114)
* Drop support for RDS PostgreSQL 9.x. (#114)
* Add support for `EKS EncryptionConfig <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-eks-cluster.html#cfn-eks-cluster-encryptionconfig>`_. Set with ``EnableEksEncryptionConfig=true``. (#115)
* Add ``EksClusterName`` parameter to control name of EKS cluster. If upgrading, set this to STACK_NAME-cluster to match existing name. (#115)
* Upgrade to troposphere v4.2.0. (#116)
* Add ``EksPublicAccessCidrs`` parameter to optionally restrict access to your public Kubernetes API endpoint using CIDR blocks. If defined, both public and private endpoint access enabled as detailed in `API server endpoint access options <https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html#modify-endpoint-access>`_. (#117)
* Enable ``api``, ``audit``, and ``authenticator`` log types for `EKS control plane logging <https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html>`_. (#117)
* Allow bastion access to Kubernetes API endpoint. (#117)
* Add ``eks.LaunchTemplateSpecification`` to enforce `HttpTokens-based metadata <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html>`_. (#117)


`2.1.2`_ (2022-03-10)
---------------------

* Automatically enable ECR image scanning in stacks with an ECR Repository
* Automatically enable Redis MultiAZ if failover is enabled
* Fix bug where EKS instances could not reach cache clusters


`2.1.1`_ (2021-02-17)
---------------------

* Fix an error in the format of ``Nodegroup`` tags


`2.1.0`_ (2021-02-17)
---------------------

* Optionally create RDS, Redis, memcached, elasticsearch services when creating
  an EKS cluster.
* Include standard aws-web-stacks public and private asset buckets when using EKS.
* Make AssetsCloudFrontCertArn empty by default so it's optional
* Make SFTPUserRole and SFTPUserScopeDownPolicy key off use_sftp_condition
* Add support for new EC2 and RDS instance types
* Add support for RDS for PostgreSQL version 12
* Add a missing ``PropagateAtLaunch`` property to ELB tags (#105)
* Remove a broken reference in the Dokku stack (#98)
* Other minor bug fixes


`2.0.0`_ (2020-03-04)
---------------------

**Backwards-incompatible changes:**

* Update RDS resource name of database to be ``DatabaseInstance`` rather than ``PostgreSQL``. While other engines were previously supported, the title within the stack still referenced PostgreSQL. **This change will force a recreation of your RDS instance.**
* Simplify the VPC layout to have 2 public and 2 private subnets. Due to this change, **updating an existing stack is not supported.**  You'll need to create a new stack and re-deploy all services within it.
* Add support to provision Memcached and Redis clusters in tandem. The resource names have been adjusted to make this change and will force creation of new instances, possibly requiring a new stack.

What's new in 2.0.0:

* Add support for Elastic Kubernetes Service (EKS).
* Re-purpose use_aes256_encryption flag to support encryption across S3, RDS, Elasticache (Redis only), and RDS (thanks @dsummersl)
* Add support for Customer Managed CMKs with ``CustomerManagedCmkArn`` parameter (not applied to public buckets)
* Add configurable ContainerVolumeSize to change root volume size of EC2 instances (thanks @dsummersl)
* Change generated template output from JSON to YAML (thanks @cchurch)
* The stack no longer prompts for a ``SECRET_KEY`` if it won't be used for the stack type in question.
* Add required DBParameterGroup by default, which allows configuring database specific parameters. This avoids having to reboot a production database instance to add a DBParameterGroup in the future. (thanks @cchurch)
* Add tags to all resources, including a common ``aws-web-stacks:stack-name`` tag with the stack's name
* Add a ``aws-web-stacks:role`` tag to EC2 instances to identify as bastion vs. worker.
* You now have the option of creating a bastion host or VPN server as part of the stack, when a
  stack with a NAT Gateway is used, to facilitate secure remote access to hosts within the VPC.
* Add a parameter to specify the default canned ACL for the public assets bucket.
* Block all public access for the private assets bucket.
* Add parameters to customize VPC and subnet IPv4 CIDR blocks (**It is generally not possible to change the CIDR blocks for an existing stack.**).
* Add RDS and ElastiCache endpoint outputs.
* Add CustomAppCertificateArn parameter to allow association with an existing ACM certificate.
* Add VPC Endpoint for S3.
* Add DatabaseReplication parameter to add a database replica (** this will fail if DatabaseBackupRetentionDays is 0.**).
* Add optional SFTP server, including S3 bucket, transfer server, and user role and scopedown policy to use when creating
  users in the transfer server.


`1.4.0`_ (2019-08-05)
---------------------

Features:

* Allow ACM certificate to be optional and/or be specified at a later date via a manual process. See
  Manual ACM Certificates in README for more information.
* Adds AdministratorIPAddress parameter so SSH access can be configured (thanks @dsummersl).
* Adds AssetsUseAES256Encryption parameter to enable AES256 encryption on asset buckets (thanks @dsummersl).
* Adds IgnorePublicAcls setting to private access buckets.
* Upgrade Circle CI to 2.0
* Miscellaneous fixes for release (thanks @cchurch)


`1.3.0`_ (2018-09-13)
---------------------

Features:

* Allow overriding parameter defaults at template creation time without having to change the
  Python code.  See `the README
  <https://github.com/caktus/aws-web-stacks/blob/main/README.rst#dokku>`_.
* Add a parameter to control whether certificates are validated by DNS or email, and default
  to DNS since GDPR has made email validation less likely to work.
* The database type of the RDS instance can now be configured (previously, only Postgres could
  be used). Note that, for backwards-compatibility reasons, the resources in the CloudFormation
  stack is still named ``PostgreSQL`` (this avoids unnecessarily recreating the RDS instance
  on pre-existing stacks). See: PR #32
* The RDS instance now supports all allowable special characters in the password field. See: PR #31
* The CloudFront distribution linked to the S3 assets bucket can now be disabled / enabled at the
  time a stack is created or updated; the CloudFront distribution now supports a custom domain name
  and SSL certificate. See: PR #30

`1.2.0`_ (2017-09-27)
---------------------

Features:

* The RDS instance, ElastiCache instance, and Elasticsearch instance can all now be optionally
  removed from the stack by setting the instance type to ``(none)`` in the relevant CloudFormation
  parameter.
* Support for using a single `Dokku <http://dokku.viewdocs.io/dokku/>`_ instance as an application
  server was added. Dokku is installed automatically on an Ubuntu 16.04 LTS instance, configured
  with the options selected via CloudFormation parameters, and provided the environment variables
  needed to access the related resources (such as the database, cache, or Elasticsearch instance)
  created with this stack. For more information, please see `the README
  <https://github.com/caktus/aws-web-stacks/blob/main/README.rst#dokku>`_.

`1.1.2`_ (2017-09-26)
---------------------

Features:

* A comma-separted list of alternate domain names may now be provided to the stack as a
  CloudFormation Parameter. Additional domains, if any, will be supplied as Allowed Origins
  in the CORS rules associated with the S3 buckets and will be added to the Subject
  Alternative Name extension of the auto-generated SSL certificate. Wildcard domains are
  supported in both cases, e.g., ``*.example.com``.

Bug fixes:

* The CloudFront distribution now passes through the ``Origin`` and related HTTP headers to
  the underlying S3 bucket. Prior to this fix, some resources (such as fonts) may have failed
  to load when accessed via the CloudFront distribution URL.

`1.1.1`_ (2017-09-14)
---------------------

Features:

* The retention period for automated RDS backups can now be customized or even disabled via
  CloudFormation parameters in the create/update stack form. The default number of retention
  days was also changed from 7 to 30. This change should not require replacement of your
  RDS instances, but as always, be on the lookout for unintended resource replacement when
  updating existing stacks. See: PR #12. Thanks @copelco for the change.

Bug fixes:

* Underscores are now allowed in database names. See: PR #13. Thanks @copelco for the change.
* The CloudFront distribution now passes querystring parameters to the origin. This provides
  a safer default for sites that may use querystring parameters to force re-fetching updated
  static media. See: PR #16
* Disabling Elasticsearch via parameters is not possible in EB and ECS environments, so this
  feature has been disabled for now. See: PR #15
* Elasticsearch has been removed from the GovCloud template, as it's not supported in that
  region.


`1.1.0`_ (2017-09-05)
-----------------------

Features:

* Support for Elasticsearch was added. See: PR #9

Bug fixes:

* While instance permissions were already limited for the EC2 and ECS configurations, Elastic
  Beanstalk instances were previously allowed to execute API actions for all AWS resources other
  than IAM. This release limits permissions granted to Elastic Beanstalk stalks considerably,
  granting permissions only previously granted to the ECS configuration, plus permissions
  included in the ``AWSElasticBeanstalkWebTier`` and ``AWSElasticBeanstalkMulticontainerDocker``
  AWS managed policies. **Please look out for and report any permission-related issues with
  Elastic Beanstalk stacks.** See: PR #11


`1.0.1`_ (2017-09-05)
-----------------------

Bug fixes:

* Remove the drop down list of Multicontainer Docker solution stacks, which was impossible to
  keep up to date. You'll need to copy/paste the current solution stack name from the `AWS
  website <http://docs.aws.amazon.com/elasticbeanstalk/latest/dg/concepts.platforms.html#concepts.platforms.mcdocker>`_.
  See: PR #10.


`1.0.0`_ (2017-08-16)
-----------------------

Features:

* A new stack type was added to support creating infrastructure with EC2 instances and an AMI of
  your choice with AWS Certificate Manager enabled (previously, the only option was to use one of
  the GovCloud stacks, which did not include an auto-generated SSL certificate). See: PR #7.

Bug fixes:

* The default ACL on the private assets bucket was previously set to  value ``authenticated-read``.
  It is now set to ``private``.

Backwards-incompatible changes:

* Support for memcached added, with ``REDIS_URL`` renamed to ``CACHE_URL`` and the associated
  CloudFormation resource renamed from ``Redis`` to ``CacheCluster``. **This change will cause your
  Redis instance to be deleted and recreated.** See: PR #8.
* Support for RDS encryption added. **This change will require your RDS instance to be deleted and
  recreated.**


`0.9.0`_ (2017-04-21)
----------------------

* Initial public release


.. _2.2.0: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=2.2.0/
.. _2.1.2: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=2.1.2/
.. _2.1.1: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=2.1.1/
.. _2.1.0: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=2.1.0/
.. _2.0.0: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=2.0.0/
.. _1.4.0: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=1.4.0/
.. _1.3.0: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=1.3.0/
.. _1.2.0: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=1.2.0/
.. _1.1.2: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=1.1.2/
.. _1.1.1: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=1.1.1/
.. _1.1.0: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=1.1.0/
.. _1.0.1: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=1.0.1/
.. _1.0.0: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=1.0.0/
.. _0.9.0: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=0.9.0/
