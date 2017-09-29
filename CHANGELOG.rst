Change Log
==========


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
  <https://github.com/caktus/aws-web-stacks/blob/master/README.rst#dokku>`_.

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


.. _1.2.0: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=1.2.0/
.. _1.1.2: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=1.1.2/
.. _1.1.1: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=1.1.1/
.. _1.1.0: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=1.1.0/
.. _1.0.1: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=1.0.1/
.. _1.0.0: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=1.0.0/
.. _0.9.0: https://aws-web-stacks.s3.amazonaws.com/index.html?prefix=0.9.0/
