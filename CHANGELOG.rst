Change Log
==========


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


.. _1.0.0: https://aws-container-basics.s3.amazonaws.com/index.html?prefix=1.0.0/
.. _0.9.0: https://aws-container-basics.s3.amazonaws.com/index.html?prefix=0.9.0/
