AWS Container Basics
====================

This repository aims to be the best library of CloudFormation templates for hosting containerized
web applications on AWS. The library supports either Elastic Container Service (ECS) or
Elastic Beanstalk (EB) and provides auxilary managed services such as a Postgres RDS instance,
Redis instance, (free) SSL certificate via AWS Certificate Manager, S3 bucket for static assets,
ECS repository for hosting Docker images, etc. All resources are created in a self-contained VPC,
which may use a NAT gateway (if you want to pay for that) or not.

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
.. _EB-No-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=eb-app-no-nat&templateURL=https://s3.amazonaws.com/aws-container-basics/eb-no-nat.json

.. |EB-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _EB-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=eb-app-with-nat&templateURL=https://s3.amazonaws.com/aws-container-basics/eb-nat.json

.. |ECS-No-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _ECS-No-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=ecs-app-no-nat&templateURL=https://s3.amazonaws.com/aws-container-basics/ecs-no-nat.json

.. |ECS-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _ECS-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=ecs-app-with-nat&templateURL=https://s3.amazonaws.com/aws-container-basics/ecs-nat.json

Environment Variables
---------------------

Once your environment is created (typically 20-30 minutes, the CloudFront distribution and RDS
instance usually take the longest), you'll have an Elastic Beanstalk (EB) or Elastic Compute Service
(ECS) environment with the environment variables you need to run a containerized web application.
These environment variables are:

* ``AWS_STORAGE_BUCKET_NAME``: The name of the S3 bucket in which your application should store
  static assets
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
	  "volumes": [
	    {
	      "name": "my-app",
	      "host": {
	        "sourcePath": "/var/app/current/my-app"
	      }
	    }
	  ],
	  "containerDefinitions": [
	    {
	      "name": "my-app",
	      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/<stack-name>:latest",
	      "essential": true,
	      "memory": 512,
	      "portMappings": [
	        {
	          "hostPort": 80,
	          "containerPort": 8000
	        }
	      ],
	      "mountPoints": [
	        {
	          "sourceVolume": "my-app",
	          "containerPath": "/var/www/html",
	          "readOnly": true
	        }
	      ]
	    }
	  ]
	}

You can add and link other container definitions, such as an Nginx proxy, if desired.

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

Copyright 2017 Jean-Phillipe Serafin, Tobias McNulty.
