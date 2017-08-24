AWS Container Basics
====================

AWS Container Basics is a library of CloudFormation templates that dramatically simplify hosting
containerized web applications on AWS. The library supports either Elastic Container Service (ECS),
Elastic Beanstalk (EB), or EC2 instances (via an AMI you specify) and provides auxilary managed
services such as a Postgres RDS instance, Redis instance, (free) SSL certificate via AWS Certificate
Manager, S3 bucket for static assets, ECS repository for hosting Docker images, etc. All resources
are created in a self-contained VPC, which may use a NAT gateway (if you want to pay for that) or not.

The CloudFormation templates are written in `troposphere <https://github.com/cloudtools/troposphere>`_,
which allows for some validation at build time and simplifies the management of several related
templates.

If a NAT gateway is not used, it's possible to create a fully-managed, self-contained hosting
environment for your application entirely within the free tier on AWS. To try it out, select
one of the following:

+---------------------+-------------------+---------------------------+---------------+
|                     | Elastic Beanstalk | Elastic Container Service | EC2 Instances |
+=====================+===================+===========================+===============+
| Without NAT Gateway | |EB-No-NAT|_      | |ECS-No-NAT|_             | |EC2-No-NAT|_ |
+---------------------+-------------------+---------------------------+---------------+
| With NAT Gateway    | |EB-NAT|_         | |ECS-NAT|_                | |EC2-NAT|_    |
+---------------------+-------------------+---------------------------+---------------+

If you'd like to review the CloudFormation template first, or update an existing stack, you may also
wish to use the JSON template directly:

+---------------------+-------------------+---------------------------+--------------------+
|                     | Elastic Beanstalk | Elastic Container Service | EC2 Instances      |
+=====================+===================+===========================+====================+
| Without NAT Gateway | `eb-no-nat.json`_ | `ecs-no-nat.json`_        | `ec2-no-nat.json`_ |
+---------------------+-------------------+---------------------------+--------------------+
| With NAT Gateway    | `eb-nat.json`_    | `ecs-nat.json`_           | `ec2-nat.json`_    |
+---------------------+-------------------+---------------------------+--------------------+

.. |EB-No-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _EB-No-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=eb-app-no-nat&templateURL=https://s3.amazonaws.com/aws-container-basics/eb-no-nat.json
.. _eb-no-nat.json: https://s3.amazonaws.com/aws-container-basics/eb-no-nat.json

.. |EB-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _EB-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=eb-app-with-nat&templateURL=https://s3.amazonaws.com/aws-container-basics/eb-nat.json
.. _eb-nat.json: https://s3.amazonaws.com/aws-container-basics/eb-nat.json

.. |ECS-No-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _ECS-No-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=ecs-app-no-nat&templateURL=https://s3.amazonaws.com/aws-container-basics/ecs-no-nat.json
.. _ecs-no-nat.json: https://s3.amazonaws.com/aws-container-basics/ecs-no-nat.json

.. |ECS-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _ECS-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=ecs-app-with-nat&templateURL=https://s3.amazonaws.com/aws-container-basics/ecs-nat.json
.. _ecs-nat.json: https://s3.amazonaws.com/aws-container-basics/ecs-nat.json

.. |EC2-No-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _EC2-No-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=ec2-app-no-nat&templateURL=https://s3.amazonaws.com/aws-container-basics/ec2-no-nat.json
.. _ec2-no-nat.json: https://s3.amazonaws.com/aws-container-basics/ec2-no-nat.json

.. |EC2-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _EC2-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=ec2-app-with-nat&templateURL=https://s3.amazonaws.com/aws-container-basics/ec2-nat.json
.. _ec2-nat.json: https://s3.amazonaws.com/aws-container-basics/ec2-nat.json

Elastic Beanstalk, Elastic Container Service, or EC2 instances?
---------------------------------------------------------------

Elastic Beanstalk is the recommended starting point, unless more complex container service
definitions are required or you prefer to configure application servers manually using Ansible,
Salt, Chef, Puppet, or another such tool. Elastic Beanstalk comes with a preconfigured autoscaling
configuration, allows for automated, managed updates to the underlying servers, allows changing
environment variables without recreating the underlying service, and comes with its own command line
tool for managing deployments. The Elastic Beanstalk environment uses the
`multicontainer docker environment <http://docs.aws.amazon.com/elasticbeanstalk/latest/dg/create_deploy_docker_ecs.html>`_
to maximize flexibility in terms of the application(s) and container(s) deployed to the stack.


NAT Gateways
------------

`NAT Gateways <http://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/vpc-nat-gateway.html>`_
have the added benefit of preventing network connections to EC2 instances within the VPC, but
come at an added cost (and no free tier).

Stack Creation Process
----------------------

Creating a stack takes approximately 30-35 minutes. The CloudFront distribution and RDS instance
typically take the longest to finish, and the EB environment or ECS service creation
will not begin until all of its dependencies, including the CloudFront distribution and RDS
instance, have been created.

SSL Certificate
---------------

The automatically-generated SSL certificate requires approval from the domain owner. After
initiating stack creation, be on the lookout for an email from Amazon to the domain owner
(as seen in a ``whois`` query) and follow the link to approve the certificate. If you're using
a ``.io`` domain, be aware that
`prior steps <http://docs.aws.amazon.com/acm/latest/userguide/troubleshoot-iodomains.html>`_
may be necessary to receive email for ``.io`` domains, because domain owner emails cannot
be discovered via ``whois``.

Resources Created
-----------------

The following is a partial list of resources created by this stack, when Elastic Beanstalk is used:

* **ApplicationRepository** (``AWS::ECR::Repository``): A Docker image repository that your EB
  environment or ECS cluster will have access to pull images from.
* **AssetsBucket** (``AWS::S3::Bucket``): An S3 bucket for storing application-related static
  assets. Permissions are set up automatically so your application can put new assets via the S3
  API.
* **AssetsDistribution** (``AWS::CloudFront::Distribution``): A CloudFront distribution
  corresponding to the above S3 bucket.
* **Certificate** (``AWS::CertificateManager::Certificate``): An SSL certificate tied to the Domain
  Name specified during setup. Note that the "Approve" link in the automated email sent to the
  domain owner as part of certificate creation must be clicked before stack creation will finish.
* **EBApplication** (``AWS::ElasticBeanstalk::Application``): The Elastic Beanstalk application.
* **EBEnvironment** (``AWS::ElasticBeanstalk::Environment``): The Elastic Beanstalk environment,
  which will be pre-configured with the environment variables specified below.
* **PostgreSQL** (``AWS::RDS::DBInstance``): The Postgres RDS instance for your application.
  Includes a security group to allow access only from your EB or ECS instances in this stack.
* **Redis** (``AWS::ElastiCache::CacheCluster``): The Redis ElasticCache instance for your
  application. Includes a cache security group to allow access only from your EB or ECS instances in
  this stack.
* **Vpc** (``AWS::EC2::VPC``): The VPC that contains all relevant stack-related resources (such as
  the EB or ECS EC2 instances, the RDS instance, and ElastiCache instance). The VPC is created with
  two subnets in different availability zones so that, for MultiAZ RDS instances or EB/ECS clusters
  with multiple EC2 instances, resources will be spread across multiple availability zones
  automatically.

GovCloud Support
----------------

`AWS GovCloud <https://aws.amazon.com/govcloud-us/>`_ does not support Elastic Beanstalk,
Elastic Container Service, Certificate Manager, or CloudFront. You can still create a reduced
stack in GovCloud by downloading one of the following templates and uploading it to CloudFormation
via the AWS Management Console:

+---------------------+-------------------+
| Without NAT Gateway | `gc-no-nat.json`_ |
+---------------------+-------------------+
| With NAT Gateway    | `gc-nat.json`_    |
+---------------------+-------------------+

.. _gc-no-nat.json: https://s3.amazonaws.com/aws-container-basics/gc-no-nat.json
.. _gc-nat.json: https://s3.amazonaws.com/aws-container-basics/gc-nat.json

This template will create:

* a VPC and the associated subnets,
* an RDS instance,
* a Redis instance
* an Elastic Load Balancer (ELB),
* an Auto Scaling Group and associated Launch Configuration, and
* the number of EC2 instances you specify during stack creation (using the specified AMI)

There is no way to manage environment variables when using straight EC2 instances like this,
so you are responsible for selecting the appropriate AMI and configuring it to serve your
application on the specified port, with all of the necessary secrets and environment variables.
Note that the Elastic Load Balancer will not direct traffic to your instances until the health
check you specify during stack creation returns a successful response.

Environment Variables
---------------------

Once your environment is created you'll have an Elastic Beanstalk (EB) or Elastic Compute Service
(ECS) environment with the environment variables you need to run a containerized web application.
These environment variables are:

* ``AWS_STORAGE_BUCKET_NAME``: The name of the S3 bucket in which your application should store
  static assets
* ``AWS_PRIVATE_STORAGE_BUCKET_NAME``: The name of the S3 bucket in which your application should
  store private/uploaded files or media. Make sure you configure your storage backend to require
  authentication to read objects and encrypt them at rest, if needed.
* ``CDN_DOMAIN_NAME``: The domain name of the CloudFront distribution connected to the above S3
  bucket; you should use this (or the S3 bucket URL directly) to refer to static assets in your HTML
* ``DOMAIN_NAME``: The domain name you specified when creating the stack, which will
  be associated with the automatically-generated SSL certificate.
* ``SECRET_KEY``: The secret key you specified when creating this stack
* ``DATABASE_URL``: The URL to the RDS instance created as part of this stack.
* ``REDIS_URL``: The URL to the Redis instance created as part of this stack (may be used as a cache
  or session storage, e.g.). Note that Redis supports multiple databases and no database ID is
  included as part of the URL, so you should append a forward slash and the integer index of the
  database, if needed, e.g., ``/0``.

When running an EB stack, you can view and edit the keys and values for all environment variables
on the fly via the Elastic Beanstalk console or command line tools.

Deployment to Elastic Beanstalk
-------------------------------

You can deploy your application to an Elastic Beanstalk stack created with this template as follows.

First, build and push your docker image to the ECR repository created by this stack (you can also
see these commands with the appropriate variables filled in by clicking the "View Push Commands"
button on the Amazon ECS Repository detail page in the AWS console)::

    $(aws ecr get-login --region <region>)  # $(..) will execute the output of the inner command
    docker build -t <stack-name> .
    docker tag <stack-name>:latest <account-id>.dkr.ecr.<region>.amazonaws.com/<stack-name>:latest
    docker push <account-id>.dkr.ecr.<region>.amazonaws.com/<stack-name>:latest

Once working, you might choose to execute these commands from the appropriate point in your CI/CD
pipeline.

Next, create a ``Dockerrun.aws.json`` file in your project directory, pointing it to the image you
just pushed::

    {
      "AWSEBDockerrunVersion": 2,
      "containerDefinitions": [
        {
          "name": "my-app",
          "image": "<account-id>.dkr.ecr.<region>.amazonaws.com/<stack-name>:latest",
          "essential": true,
          "memory": 512,
          "portMappings": [
            {
              "hostPort": 80,
              "containerPort": 8000
            }
          ],
          "logConfiguration": {
            "logDriver": "awslogs",
            "options": {
              "awslogs-region": "<region>",
              "awslogs-group": "<log group>",
              "awslogs-stream-prefix": "my-app"
            }
          }
        }
      ]
    }

You can add and link other container definitions, such as an Nginx proxy or background task
workers, if desired.

A single CloudWatch Logs group will be created for you. You can find its name by navigating
to the AWS CloudWatch Logs console (after stack creation has finished). If prefer to create
your own log group, you can do so with the ``aws`` command line tool::

    pip install -U awscli
    aws logs create-log-group --log-group-name <log-group-name> --region <region>

Finally, you'll need to install the AWS and EB command line tools, commit or stage for commit the
``Dockerrun.aws.json`` file, and deploy the application::

    pip install -U awscli awsebcli
    git add Dockerrun.aws.json
    eb init  # select the existing EB application and environment, when prompted
    eb deploy --staged  # or just `eb deploy` if you've committed Dockerrun.aws.json

Once complete, the EB environment should be running a copy of your container. To troubleshoot any
issues with the deployment, review events and logs via the Elastic Beanstack section of the AWS
console.

Good luck!

Contributing
------------

Please read `contributing guidelines here <https://github.com/tobiasmcnulty/aws-container-basics/blob/develop/CONTRIBUTING.rst>`_.

Copyright 2017 Jean-Phillipe Serafin, Tobias McNulty.
