AWS Container Basics
====================

This repository aims to be the best library of CloudFormation templates for hosting containerized
web applications on AWS. The library supports either Elastic Container Service (ECS) or
Elastic Beanstalk (EB) and provides auxilary managed services such as a Postgres RDS instance,
Redis instance, (free) SSL certificate via AWS Certificate Manager, S3 bucket for static assets,
etc. All resources are created in a self-contained VPC, which may use a NAT gateway (if you
want to pay for that) or not.

The CloudFormation templates are written in `troposphere <https://github.com/cloudtools/troposphere>`_,
which allows for some validation at build time and simplifies the management of several related
templates.

If a NAT gateway is not used, it's possible to create a fully-managed, self-contained hosting
environment for your application entirely within the free tier on AWS. To try it out, select
one of the following:

+---------------------+-------------------+---------------------------+
|                     | Elastic Beanstalk | Elastic Container Service |
+=====================+===================+===========================+
| Without NAT Gateway | |EB-No-NAT|_      | |ECS-No-NAT|_             |
+---------------------+-------------------+---------------------------+
| With NAT Gateway    | |EB-NAT|_         | |ECS-NAT|_                |
+---------------------+-------------------+---------------------------+

.. |EB-No-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _EB-No-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=eb-app&templateURL=https://s3.amazonaws.com/aws-container-basics/eb-no-nat.json

.. |EB-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _EB-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=eb-app&templateURL=https://s3.amazonaws.com/aws-container-basics/eb-nat.json

.. |ECS-No-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _ECS-No-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=eb-app&templateURL=https://s3.amazonaws.com/aws-container-basics/ecs-no-nat.json

.. |ECS-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _ECS-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=eb-app&templateURL=https://s3.amazonaws.com/aws-container-basics/ecs-nat.json


Copyright 2017 Jean-Phillipe Serafin, Tobias McNulty.
