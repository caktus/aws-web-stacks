AWS Web Stacks
==============

.. image:: https://circleci.com/gh/caktus/aws-web-stacks.svg?style=svg
    :target: https://circleci.com/gh/caktus/aws-web-stacks

AWS Web Stacks is a library of CloudFormation templates that dramatically simplify hosting web applications
on AWS. The library supports using Elastic Container Service (ECS), Elastic Beanstalk (EB), EC2 instances
(via an AMI you specify), or `Dokku <http://dokku.viewdocs.io/dokku/>`_ for the application server(s) and
provides auxilary managed services such as an RDS instance, ElastiCache instance, Elasticsearch instance
(free) SSL certificate via AWS Certificate Manager, S3 bucket for static assets, ECS repository for hosting
Docker images, etc. All resources (that support VPCs) are created in a self-contained VPC, which may use a
NAT gateway (if you want to pay for that) or not, and resources that require API authentication (such as
S3 or Elasticsearch) are granted permissions via the IAM instance role and profile assigned to the
application servers created in the stack.

The CloudFormation templates are written in `troposphere <https://github.com/cloudtools/troposphere>`_,
which allows for some validation at build time and simplifies the management of several related
templates.

If a NAT gateway is not used, it's possible to create a fully-managed, self-contained hosting
environment for your application entirely within the free tier on AWS (albeit not with all stacks,
for example, there is no free tier for EKS). To try it out, select one of the following:

+---------------------+-------------------+---------------------------+---------------+-----------------+---------------+
|                     | Elastic Beanstalk | Elastic Container Service | EC2 Instances | Dokku           | EKS           |
+=====================+===================+===========================+===============+=================+===============+
| Without NAT Gateway | |EB-No-NAT|_      | |ECS-No-NAT|_             | |EC2-No-NAT|_ | |Dokku-No-NAT|_ | |EKS-No-NAT|_ |
+---------------------+-------------------+---------------------------+---------------+-----------------+---------------+
| With NAT Gateway    | |EB-NAT|_         | |ECS-NAT|_                | |EC2-NAT|_    | n/a             | |EKS-NAT|_    |
+---------------------+-------------------+---------------------------+---------------+-----------------+---------------+

If you'd like to review the CloudFormation template first, or update an existing stack, you may also
wish to use the YAML template directly:

+---------------------+-------------------+---------------------------+--------------------+----------------------+--------------------+
|                     | Elastic Beanstalk | Elastic Container Service | EC2 Instances      | Dokku                | EKS                |
+=====================+===================+===========================+====================+======================+====================+
| Without NAT Gateway | `eb-no-nat.yaml`_ | `ecs-no-nat.yaml`_        | `ec2-no-nat.yaml`_ | `dokku-no-nat.yaml`_ | `eks-no-nat.yaml`_ |
+---------------------+-------------------+---------------------------+--------------------+----------------------+--------------------+
| With NAT Gateway    | `eb-nat.yaml`_    | `ecs-nat.yaml`_           | `ec2-nat.yaml`_    | n/a                  | `eks-nat.yaml`_    |
+---------------------+-------------------+---------------------------+--------------------+----------------------+--------------------+

.. |EB-No-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _EB-No-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=eb-app-no-nat&templateURL=https://s3.amazonaws.com/aws-web-stacks/eb-no-nat.yaml
.. _eb-no-nat.yaml: https://s3.amazonaws.com/aws-web-stacks/eb-no-nat.yaml

.. |EB-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _EB-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=eb-app-with-nat&templateURL=https://s3.amazonaws.com/aws-web-stacks/eb-nat.yaml
.. _eb-nat.yaml: https://s3.amazonaws.com/aws-web-stacks/eb-nat.yaml

.. |ECS-No-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _ECS-No-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=ecs-app-no-nat&templateURL=https://s3.amazonaws.com/aws-web-stacks/ecs-no-nat.yaml
.. _ecs-no-nat.yaml: https://s3.amazonaws.com/aws-web-stacks/ecs-no-nat.yaml

.. |ECS-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _ECS-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=ecs-app-with-nat&templateURL=https://s3.amazonaws.com/aws-web-stacks/ecs-nat.yaml
.. _ecs-nat.yaml: https://s3.amazonaws.com/aws-web-stacks/ecs-nat.yaml

.. |EC2-No-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _EC2-No-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=ec2-app-no-nat&templateURL=https://s3.amazonaws.com/aws-web-stacks/ec2-no-nat.yaml
.. _ec2-no-nat.yaml: https://s3.amazonaws.com/aws-web-stacks/ec2-no-nat.yaml

.. |EC2-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _EC2-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=ec2-app-with-nat&templateURL=https://s3.amazonaws.com/aws-web-stacks/ec2-nat.yaml
.. _ec2-nat.yaml: https://s3.amazonaws.com/aws-web-stacks/ec2-nat.yaml

.. |Dokku-No-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _Dokku-No-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=dokku-no-nat&templateURL=https://s3.amazonaws.com/aws-web-stacks/dokku-no-nat.yaml
.. _dokku-no-nat.yaml: https://s3.amazonaws.com/aws-web-stacks/dokku-no-nat.yaml

.. |EKS-No-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _EKS-No-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=eks-no-nat&templateURL=https://s3.amazonaws.com/aws-web-stacks/eks-no-nat.yaml
.. _eks-no-nat.yaml: https://s3.amazonaws.com/aws-web-stacks/eks-no-nat.yaml

.. |EKS-NAT| image:: https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png
.. _EKS-NAT: https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=eks-with-nat&templateURL=https://s3.amazonaws.com/aws-web-stacks/eks-nat.yaml
.. _eks-nat.yaml: https://s3.amazonaws.com/aws-web-stacks/eks-nat.yaml

Documentation
-------------

In addition to this README, there is additional documentation at
http://aws-web-stacks.readthedocs.io/


Elastic Beanstalk, Elastic Container Service, EC2, Dokku, or EKS?
-----------------------------------------------------------------

**Elastic Beanstalk** is the recommended starting point. Elastic Beanstalk comes with a preconfigured
autoscaling configuration, allows for automated, managed updates to the underlying servers, allows changing
environment variables without recreating the underlying service, and comes with its own command line
tool for managing deployments. The Elastic Beanstalk environment uses the
`multicontainer docker environment <http://docs.aws.amazon.com/elasticbeanstalk/latest/dg/create_deploy_docker_ecs.html>`_
to maximize flexibility in terms of the application(s) and container(s) deployed to the stack.

**Elastic Container Service (ECS)** or **Elastic Kubernetes Service (EKS)** might be useful if complex container
service definitions are required.

If you prefer to configure application servers manually using Ansible, Salt, Chef, Puppet, or another such tool,
choose the **EC2** option. Be aware that the instances created are managed by an autoscaling group, so you should
suspend the autoscaling processes on this autoscaling group (after the initial instances are created) if you
don't want it to bring up new (unprovisioned) instances or potentially even terminate one of your instances should
it appear unhealthy, e.g.::

    aws autoscaling suspend-processes --auto-scaling-group-name <your-ag-name>

For very simple, Heroku-like deploys, choose the **Dokku** option. This will give you a single EC2 instance
based on Ubuntu 16.04 LTS with `Dokku <http://dokku.viewdocs.io/dokku/>`_ pre-installed and global environment
variables configured that will allow your app to find the RDS, ElastiCache, and Elasticsearch nodes created
with this stack.

NAT Gateways
------------

`NAT Gateways <http://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/vpc-nat-gateway.html>`_
have the added benefit of preventing network connections to EC2 instances within the VPC, but
come at an added cost (and no free tier).

If a NAT Gateway stack is selected, you'll have the option of creating a bastion host or VPN server
in the stack, using an AMI and instance type of your choice. The bastion type selected will determine which
ports are opened by default for this host. If ``SSH``, only SSH traffic will be allowed from the IP address
or subnet configured by the ``AdministratorIPAddress`` parameter. If ``OpenVPN``, HTTPS and SSH traffic will
be allowed from the ``AdministratorIPAddress``, and OpenVPN UDP traffic from any address. Additional ports
will need to be opened manually via the AWS console or API.

Stack Creation Process
----------------------

Creating a stack takes approximately 30-35 minutes. The CloudFront distribution and RDS instance
typically take the longest to finish, and the EB environment or ECS service creation
will not begin until all of its dependencies, including the CloudFront distribution and RDS
instance, have been created.

EKS Worker Nodes
----------------

The EKS stack includes EKS worker nodes, however, they will not be allowed to join the cluster
until you specifically grant them access as described in the `AWS EKS User Guide
<https://docs.aws.amazon.com/eks/latest/userguide/launch-workers.html>`_. In short, you need to:

1. Download the AWS IAM Authenticator configuration map template from AWS::

    curl -o aws-auth-cm.yaml https://amazon-eks.s3-us-west-2.amazonaws.com/cloudformation/2019-10-08/aws-auth-cm.yaml

2. Open the file with your favorite text editor. Replace the ``<ARN of instance role (not instance profile)>``
   snippet with the ``ContainerInstanceRole`` ARN from the stack that you created, and save the file.
   **Important:** Do not modify any other lines in this file.

3. Apply the configuration::

    kubectl apply -f aws-auth-cm.yaml

If you your nodes still aren't joining the cluster, consult the AWS EKS User Guide.

SSL Certificate
---------------

For the Elastic Beanstalk, Elastic Container Service, and EC2 (non-GovCloud) options, an
automatically-generated SSL certificate is included. The certificate requires approval from the
domain owner before it can be issued, and *your stack creation will not finish until you approve
the request*. Be on the lookout for an email from Amazon to the domain owner (as seen in a ``whois``
query) and follow the link to approve the certificate. If you're using a ``.io`` domain, be aware that
`prior steps <http://docs.aws.amazon.com/acm/latest/userguide/troubleshoot-iodomains.html>`_
may be necessary to receive email for ``.io`` domains, because domain owner emails cannot
be discovered via ``whois``.

Manual ACM Certificates
~~~~~~~~~~~~~~~~~~~~~~~

You also have the option to *not* create a certificate as part of the stack provisioning process. If
you do this, an HTTPS listener (and corresponding certificate) can be manually attached to the load
balancer after stack creation via the AWS Console or using ``awscli`` using the steps below.

To request a new certificate using DNS validation, run the following command with ``--domain-name``
matching your desired domain::

  aws acm request-certificate --domain-name [DOMAIN NAME] --validation-method DNS

You can query the CNAME ``name`` and ``value`` variables using ``describe-certificate``::

  aws acm list-certificates
  aws acm describe-certificate --certificate-arn=YOUR-CertificateArn

Add the listed CNAME to your DNS provider to complete the verification process.

Once verified, add an HTTPS listener to the environment's ELB::

  aws elb describe-load-balancers --query "LoadBalancerDescriptions[*].LoadBalancerName"
  aws elb create-load-balancer-listeners --load-balancer-name [LB NAME]
                                         --listeners "SSLCertificateId=[CERTIFICATE-ARN],Protocol=HTTPS,LoadBalancerPort=443,InstanceProtocol=HTTP,InstancePort=80"


Encryption (using AWS Key Management Service)
---------------------------------------------

Server-side encryption support is available, via the ``UseAES256Encryption``
parameter, on the following AWS resources:

* EC2 EBS (for application EC2 instances and bastion host)
* ElastiCache Redis (ReplicationGroup)
* RDS
* S3

By default, when enabled, an `AWS managed CMK`_ (customer master key) will be
created the first time you try to create an encrypted resource within that
service. AWS will manage the policies associated with AWS managed CMKs on your
behalf. You can track AWS managed keys in your account and all usage is logged
in AWS CloudTrail, but you have no direct control over the keys themselves.
These keys will be shared across all resources utilizing default encryption
within your AWS account.

Customer Managed CMK
~~~~~~~~~~~~~~~~~~~~

The ``CustomerManagedCmkArn`` parameter allows your stack to be encrypted with a
`Customer Managed CMK`_. You have full control over these CMKs, including
establishing and maintaining their key policies, IAM policies, and grants,
enabling and disabling them, rotating their cryptographic material, adding tags,
creating aliases that refer to the CMK, and scheduling the CMKs for deletion.

Required CMK Key Policy for Use with Encrypted Volumes
``````````````````````````````````````````````````````

**Important:** If you specify a customer managed CMK, several steps are required
to support Amazon EBS encryption within Amazon EC2 Auto Scaling.

1. You (or your account administrator) must give the appropriate
**service-linked role** access to the CMK, so that Amazon EC2 Auto Scaling can
launch instances on your behalf. To do this, you must modify the CMK's key
policy. If omitted, auto scaling will fail to launch instances. See `Required
CMK Key Policy for Use with Encrypted Volumes`_ for more information.

2. You must encrypt the AMI specified in the ``AMI`` parameter with your
customer managed CMK. Existing AMIs can easily be copied and encrypted with your
key from within the AWS Console. Follow the steps in `Copying an AMI`_ and use
your customer managed CMK ARN when prompted for a Master Key. Once copied, use
the new AMI for your stack ``AMI`` parameter.

.. _AWS managed CMK: https://docs.aws.amazon.com/en_pv/kms/latest/developerguide/concepts.html#aws-managed-cmk
.. _Customer Managed CMK: https://docs.aws.amazon.com/en_pv/kms/latest/developerguide/concepts.html#customer-cmk
.. _Required CMK Key Policy for Use with Encrypted Volumes: https://docs.aws.amazon.com/en_pv/autoscaling/ec2/userguide/key-policy-requirements-EBS-encryption.html
.. _Copying an AMI: https://docs.aws.amazon.com/en_pv/AWSEC2/latest/UserGuide/CopyingAMIs#ami-copy-steps

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
* **Elasticsearch** (``AWS::Elasticsearch::Domain``): An Elasticsearch instance, which your
  application may use for full-text search, logging, etc.
* **PostgreSQL** (``AWS::RDS::DBInstance``): The RDS instance for your application.
  Includes a security group to allow access only from your EB or ECS instances in this stack. Note:
  this CloudFormation resource is named "PostgreSQL" for backwards-compatibility reasons, but the
  RDS instance can be configured with any database engine supported by RDS.
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

`AWS GovCloud <https://aws.amazon.com/govcloud-us/>`_ does not support Elastic Beanstalk, Elastic
Container Service, Certificate Manager, CloudFront, or Elasticsearch. You can still create a reduced
stack in GovCloud by downloading one of the following templates and uploading it to CloudFormation
via the AWS Management Console:

+---------------------+-------------------+
| Without NAT Gateway | `gc-no-nat.yaml`_ |
+---------------------+-------------------+
| With NAT Gateway    | `gc-nat.yaml`_    |
+---------------------+-------------------+

.. _gc-no-nat.yaml: https://s3.amazonaws.com/aws-web-stacks/gc-no-nat.yaml
.. _gc-nat.yaml: https://s3.amazonaws.com/aws-web-stacks/gc-nat.yaml

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

Environment Variables within your server instances
--------------------------------------------------

Once your environment is created you'll have an Elastic Beanstalk (EB) or Elastic Compute Service
(ECS) environment with the environment variables you need to run a containerized web application.
These environment variables are:

* ``AWS_REGION``: The AWS region in which your stack was created.
* ``AWS_STORAGE_BUCKET_NAME``: The name of the S3 bucket in which your application should store
  static assets
* ``AWS_PRIVATE_STORAGE_BUCKET_NAME``: The name of the S3 bucket in which your application should
  store private/uploaded files or media. Make sure you configure your storage backend to require
  authentication to read objects and encrypt them at rest, if needed.
* ``CDN_DOMAIN_NAME``: The domain name of the CloudFront distribution connected to the above S3
  bucket; you should use this (or the S3 bucket URL directly) to refer to static assets in your HTML
* ``ELASTICSEARCH_ENDPOINT``: The domain name of the Elasticsearch instance. If ``(none)`` is selected
  for the ``ElasticsearchInstanceType`` during stack creation, the value of this variable will be
  an empty string (``''``).
* ``ELASTICSEARCH_PORT``: The recommended port for connecting to Elasticsearch (defaults to 443).
* ``ELASTICSEARCH_USE_SSL``: Whether or not to use SSL (defaults to ``'on'``).
* ``ELASTICSEARCH_VERIFY_CERTS``: Whether or not to verify Elasticsearch SSL certificates. This
  should work fine with AWS Elasticsearch (the instance provides a valid certificate), so this
  defaults to ``'on'`` as well.
* ``DOMAIN_NAME``: The domain name you specified when creating the stack, which will
  be associated with the automatically-generated SSL certificate and as an allowed origin in the
  CORS configuration for the S3 buckets.
* ``ALTERNATE_DOMAIN_NAMES``: A comma-separated list of alternate domain names provided to the
  stack. These domains, if any, will also be included in the automatically-generated SSL certificate
  and S3 CORS configuration.
* ``SECRET_KEY``: The secret key you specified when creating this stack
* ``DATABASE_URL``: The URL to the RDS instance created as part of this stack. If ``(none)`` is
  selected for the ``DatabaseClass`` during stack creation, the value of this variable will be
  an empty string (``''``).
* ``CACHE_URL``: The URL to the Redis or Memcached instance created as part of this stack (may be
  used as a cache or session storage, e.g.). If using Redis, note that it supports multiple
  databases and no database ID is included as part of the URL, so you should append a forward slash
  and the integer index of the database, if needed, e.g., ``/0``. If ``(none)`` is selected for the
  ``CacheNodeType`` during stack creation, the value of this variable will be an empty string
  (``''``).

When running an EB stack, you can view and edit the keys and values for all environment variables
on the fly via the Elastic Beanstalk console or command line tools.

Elasticsearch Authentication
----------------------------

Since AWS Elasticsearch does not support VPCs, the Elasticsearch instance in this stack does not
accept connections from all clients. The default policy associated with the instance requires
HTTP(S) requests to be signed using the `AWS Signature Version 4
<http://docs.aws.amazon.com/general/latest/gr/sigv4_signing.html>`_. The instance role associated
with the EC2 instances created in this stack (whether using Elastic Beanstalk, Elastic Container
Service, or EC2 directly) is authorized to make requests to the Elasticsearch instance. Those
credentials may be obtained from the `EC2 instance meta data
<http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html#instance-metadata-security-credentials>`_.

If you're using Python, credentials may be obtained automatically using Boto and requests signed
using the `aws-requests-auth <https://github.com/DavidMuller/aws-requests-auth#using-boto-to-automatically-gather-aws-credentials>`_
package.

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

Dokku
-----

When creating a Dokku stack, you may find it advantageous to upload your normal SSH public key to
AWS, rather than using one that AWS generates. This way, you'll already be set up to deploy to your
Dokku instance without needing to keep track of an extra SSH private key.

The CloudFormation stack creation should not finish until Dokku is fully installed; `cfn-signal
<http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-signal.html>`_ is used in the
template to signal CloudFormation once the installation is complete.

DNS
~~~

After the stack is created, you'll want to inspect the Outputs for the PublicIP of the instance and
create a DNS ``A`` record (possibly including a wildcard record, if you're using vhost-based apps)
for your chosen domain.

For help creating a DNS record, please refer to the `Dokku DNS documentation
<http://dokku.viewdocs.io/dokku/configuration/dns/>`_.

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

The environment variables for the other resources created in this stack will be passed to Dokku
as global environment variables.

If metadata associated with the Dokku EC2 instance changes, updates to environment variables, if
any, will be passed to the live server via `cfn-hup
<http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-hup.html>`_. Depending on the
nature of the update this may or may not result the instance being stopped and restarted. Inspect
the stack update confirmation page carefully to avoid any unexpected instance recreations.

Deployment
~~~~~~~~~~

You can create a new app on the remote server like so, using the same SSH key that you specified
during the stack creation process (if you didn't use your shell's default SSH key, you'll need to
add ``-i /path/to/private_key`` to this command)::

    ssh dokku@<your domain or IP> apps:create python-sample

and then deploy Heroku's Python sample to that app::

    git clone https://github.com/heroku/python-sample.git
    cd python-sample
    git remote add dokku dokku@<your domain or IP>:python-sample
    git push dokku master

You should be able to watch the build complete in the output from the ``git push`` command. If the
deploy completes successfully, you should be able to see "Hello world!" at
http://python-sample.your.domain/

For additional help deploying to your new instance, please refer to the `Dokku documentation
<http://dokku.viewdocs.io/dokku/deployment/application-deployment/>`_.

Let's Encrypt
~~~~~~~~~~~~~

The Dokku stack does not create a load balancer and hence does not include a free SSL certificate
via Amazon Certificate Manager, so let's create one with the Let's Encrypt plugin, and add a cron
job to automatically renew the cert as needed::

    ssh ubuntu@<your domain or IP> sudo dokku plugin:install https://github.com/dokku/dokku-letsencrypt.git
    ssh dokku@<your domain or IP> config:set --no-restart python-sample DOKKU_LETSENCRYPT_EMAIL=your@email.tld
    ssh dokku@<your domain or IP> letsencrypt python-sample
    ssh dokku@<your domain or IP> letsencrypt:cron-job --add python-sample

The Python sample app should now be accessible over HTTPS at https://python-sample.your.domain/

Creating or updating templates
------------------------------

Templates built from the latest release of aws-web-stacks will be available in
S3 (see links near the top of this file). They're built with generic defaults.

Templates are built by setting some environment variables with your preferences
and then running ``python -c 'import stack'`` (see the Makefile).
The template file is output to standard output. It's easy to do this on one line::

    USE_EC2=on python -c 'import stack' >my_ec2_stack_template.yaml

Here are the environment variables that control the template creation.

USE_EC2=on
    Create EC2 instances directly.
USE_GOVCLOUD=on
    Create EC2 instances directly, but disables AWS services that aren't available
    in GovCloud like the AWS Certificate Manager and Elastic Search.
USE_EB=on
    Create an Elastic Beanstalk application
USE_ECS=on
    Create an Elastic Container Service.
USE_DOKKU=on
    Create an EC2 instance containing a Dokku server

I believe those environment variables are mutually exclusive.  The remaining
ones can be used in combination with each other or one of the above.

USE_NAT_GATEWAY=on
    Don't put the services inside your VPC onto the public internet, and
    add a NAT gateway to the stack to the services can make connections out.
DEFAULTS_FILE=<path to JSON file>
    Changes the default values for parameters. The JSON file should just be
    a dictionary mapping parameter names to default values, e.g.::

        {
            "AMI": "ami-078c57a94e9bdc6e0",
            "AssetsUseCloudFront": "false"
        }

One more example, creating EC2 instances without a NAT gateway and overriding
the parameter defaults::

    USE_EC2=on DEFAULTS_FILE=stack_defaults.json python -c 'import stack' >stack.yaml

Contributing
------------

Please read `contributing guidelines here <https://github.com/caktus/aws-web-stacks/blob/develop/CONTRIBUTING.rst>`_.

Good luck and have fun!

Copyright 2017, 2018 Jean-Phillipe Serafin, Tobias McNulty.
