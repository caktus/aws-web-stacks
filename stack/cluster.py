from troposphere import (
    AWS_ACCOUNT_ID,
    AWS_REGION,
    AWS_STACK_ID,
    AWS_STACK_NAME,
    autoscaling,
    Base64,
    cloudformation,
    elasticloadbalancing as elb,
    Equals,
    FindInMap,
    GetAtt,
    iam,
    Join,
    Not,
    Output,
    Parameter,
    Ref,
)

from troposphere.ec2 import (
    SecurityGroup,
    SecurityGroupRule,
)

from troposphere.ecs import (
    Cluster,
    ContainerDefinition,
    Environment,
    LoadBalancer,
    PortMapping,
    Service,
    TaskDefinition,
)

from awacs import ecr

from .template import template
from .vpc import (
    vpc,
    loadbalancer_a_subnet,
    loadbalancer_a_subnet_cidr,
    loadbalancer_b_subnet,
    loadbalancer_b_subnet_cidr,
    container_a_subnet,
    container_b_subnet,
)
from .assets import (
    assets_bucket,
)
from .repository import repository


certificate_id = Ref(template.add_parameter(Parameter(
    "CertId",
    Description="Web SSL certificate id",
    Type="String",
)))


container_instance_type = Ref(template.add_parameter(Parameter(
    "ContainerInstanceType",
    Description="The container instance type",
    Type="String",
    Default="t2.micro",
    AllowedValues=["t2.micro", "t2.small", "t2.medium"]
)))


web_worker_port = Ref(template.add_parameter(Parameter(
    "WebWorkerPort",
    Description="Web worker container exposed port",
    Type="Number",
    Default="8000",
)))


web_worker_cpu = Ref(template.add_parameter(Parameter(
    "WebWorkerCPU",
    Description="Web worker CPU units",
    Type="Number",
    Default="512",
)))


web_worker_memory = Ref(template.add_parameter(Parameter(
    "WebWorkerMemory",
    Description="Web worker memory",
    Type="Number",
    Default="700",
)))


web_worker_desired_count = Ref(template.add_parameter(Parameter(
    "WebWorkerDesiredCount",
    Description="Web worker task instance count",
    Type="Number",
    Default="2",
)))


max_container_instances = Ref(template.add_parameter(Parameter(
    "MaxScale",
    Description="Maximum container instances count",
    Type="Number",
    Default="3",
)))


desired_container_instances = Ref(template.add_parameter(Parameter(
    "DesiredScale",
    Description="Desired container instances count",
    Type="Number",
    Default="3",
)))


app_revision = Ref(template.add_parameter(Parameter(
    "WebAppRevision",
    Description="An optional docker app revision to deploy",
    Type="String",
    Default="",
)))


deploy_condition = "Deploy"
template.add_condition(deploy_condition, Not(Equals(app_revision, "")))


template.add_mapping("ECSRegionMap", {
    "eu-west-1": {"AMI": "ami-4e6ffe3d"},
    "us-east-1": {"AMI": "ami-8f7687e2"},
    "us-west-2": {"AMI": "ami-84b44de4"},
})


# Web load balancer
load_balancer_security_group = SecurityGroup(
    "LoadBalancerSecurityGroup",
    template=template,
    GroupDescription="Web load balancer security group.",
    VpcId=Ref(vpc),
    SecurityGroupIngress=[
        SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="443",
            ToPort="443",
            CidrIp='0.0.0.0/0',
        ),
    ],
)

load_balancer = elb.LoadBalancer(
    'LoadBalancer',
    template=template,
    Subnets=[
        Ref(loadbalancer_a_subnet),
        Ref(loadbalancer_b_subnet),
    ],
    SecurityGroups=[Ref(load_balancer_security_group)],
    Listeners=[elb.Listener(
        LoadBalancerPort=443,
        InstanceProtocol='HTTP',
        InstancePort=web_worker_port,
        Protocol='HTTPS',
        SSLCertificateId=certificate_id,
    )],
    HealthCheck=elb.HealthCheck(
        Target=Join("", ["HTTP:", web_worker_port, "/health-check"]),
        HealthyThreshold="2",
        UnhealthyThreshold="2",
        Interval="100",
        Timeout="10",
    ),
    CrossZone=True,
)

template.add_output(Output(
    "LoadBalancerDNSName",
    Description="Loadbalancer DNS",
    Value=GetAtt(load_balancer, "DNSName")
))


# ECS cluster
cluster = Cluster(
    "Cluster",
    template=template,
)


# ECS container role
container_instance_role = iam.Role(
    "ContainerInstanceRole",
    template=template,
    AssumeRolePolicyDocument=dict(Statement=[dict(
        Effect="Allow",
        Principal=dict(Service=["ec2.amazonaws.com"]),
        Action=["sts:AssumeRole"],
    )]),
    Path="/",
    Policies=[
        iam.Policy(
            PolicyName="AssetsManagementPolicy",
            PolicyDocument=dict(
                Statement=[dict(
                    Effect="Allow",
                    Action=[
                        "s3:ListBucket",
                    ],
                    Resource=Join("", [
                        "arn:aws:s3:::",
                        Ref(assets_bucket),
                    ]),
                ), dict(
                    Effect="Allow",
                    Action=[
                        "s3:*",
                    ],
                    Resource=Join("", [
                        "arn:aws:s3:::",
                        Ref(assets_bucket),
                        "/*",
                    ]),
                )],
            ),
        ),
        iam.Policy(
            PolicyName="ECSManagementPolicy",
            PolicyDocument=dict(
                Statement=[dict(
                    Effect="Allow",
                    Action=[
                        "ecs:*",
                        "elasticloadbalancing:*",
                    ],
                    Resource="*",
                )],
            ),
        ),
        iam.Policy(
            PolicyName='ECRManagementPolicy',
            PolicyDocument=dict(
                Statement=[dict(
                    Effect='Allow',
                    Action=[
                        ecr.GetAuthorizationToken,
                        ecr.GetDownloadUrlForLayer,
                        ecr.BatchGetImage,
                        ecr.BatchCheckLayerAvailability,
                    ],
                    Resource="*",
                )],
            ),
        ),
    ]
)


# ECS container instance profile
container_instance_profile = iam.InstanceProfile(
    "ContainerInstanceProfile",
    template=template,
    Path="/",
    Roles=[Ref(container_instance_role)],
)


container_security_group = SecurityGroup(
    'ContainerSecurityGroup',
    template=template,
    GroupDescription="Container security group.",
    VpcId=Ref(vpc),
    SecurityGroupIngress=[
        # HTTP from web public subnets
        SecurityGroupRule(
            IpProtocol="tcp",
            FromPort=web_worker_port,
            ToPort=web_worker_port,
            CidrIp=loadbalancer_a_subnet_cidr,
        ),
        SecurityGroupRule(
            IpProtocol="tcp",
            FromPort=web_worker_port,
            ToPort=web_worker_port,
            CidrIp=loadbalancer_b_subnet_cidr,
        ),
    ],
)


container_instance_configuration_name = "ContainerLaunchConfiguration"


autoscaling_group_name = "AutoScalingGroup"


container_instance_configuration = autoscaling.LaunchConfiguration(
    container_instance_configuration_name,
    template=template,
    Metadata=autoscaling.Metadata(
        cloudformation.Init(dict(
            config=cloudformation.InitConfig(
                commands=dict(
                    register_cluster=dict(command=Join("", [
                        "#!/bin/bash\n",
                        # Register the cluster
                        "echo ECS_CLUSTER=",
                        Ref(cluster),
                        " >> /etc/ecs/ecs.config\n",
                    ]))
                ),
                files=cloudformation.InitFiles({
                    "/etc/cfn/cfn-hup.conf": cloudformation.InitFile(
                        content=Join("", [
                            "[main]\n",
                            "template=",
                            Ref(AWS_STACK_ID),
                            "\n",
                            "region=",
                            Ref(AWS_REGION),
                            "\n",
                        ]),
                        mode="000400",
                        owner="root",
                        group="root",
                    ),
                    "/etc/cfn/hooks.d/cfn-auto-reload.conf":
                    cloudformation.InitFile(
                        content=Join("", [
                            "[cfn-auto-reloader-hook]\n",
                            "triggers=post.update\n",
                            "path=Resources.%s."
                            % container_instance_configuration_name,
                            "Metadata.AWS::CloudFormation::Init\n",
                            "action=/opt/aws/bin/cfn-init -v ",
                            "         --stack",
                            Ref(AWS_STACK_NAME),
                            "         --resource %s"
                            % container_instance_configuration_name,
                            "         --region ",
                            Ref("AWS::Region"),
                            "\n",
                            "runas=root\n",
                        ])
                    )
                }),
                services=dict(
                    sysvinit=cloudformation.InitServices({
                        'cfn-hup': cloudformation.InitService(
                            enabled=True,
                            ensureRunning=True,
                            files=[
                                "/etc/cfn/cfn-hup.conf",
                                "/etc/cfn/hooks.d/cfn-auto-reloader.conf",
                            ]
                        ),
                    })
                )
            )
        ))
    ),
    SecurityGroups=[Ref(container_security_group)],
    InstanceType=container_instance_type,
    ImageId=FindInMap("ECSRegionMap", Ref(AWS_REGION), "AMI"),
    IamInstanceProfile=Ref(container_instance_profile),
    UserData=Base64(Join('', [
        "#!/bin/bash -xe\n",
        "yum install -y aws-cfn-bootstrap\n",

        "/opt/aws/bin/cfn-init -v ",
        "         --stack", Ref(AWS_STACK_NAME),
        "         --resource %s " % container_instance_configuration_name,
        "         --region ", Ref(AWS_REGION), "\n",
    ])),
)


autoscaling_group = autoscaling.AutoScalingGroup(
    autoscaling_group_name,
    template=template,
    VPCZoneIdentifier=[Ref(container_a_subnet), Ref(container_b_subnet)],
    MinSize=desired_container_instances,
    MaxSize=max_container_instances,
    DesiredCapacity=desired_container_instances,
    LaunchConfigurationName=Ref(container_instance_configuration),
    LoadBalancerNames=[Ref(load_balancer)],
    # Since one instance within the group is a reserved slot
    # for rolling ECS service upgrade, it's not possible to rely
    # on a "dockerized" `ELB` health-check, else this reserved
    # instance will be flagged as `unhealthy` and won't stop respawning'
    HealthCheckType="EC2",
    HealthCheckGracePeriod=300,
)


# ECS task
web_task_definition = TaskDefinition(
    "WebTask",
    template=template,
    Condition=deploy_condition,
    ContainerDefinitions=[
        ContainerDefinition(
            Name="WebWorker",
            #  1024 is full CPU
            Cpu=web_worker_cpu,
            Memory=web_worker_memory,
            Essential=True,
            Image=Join("", [
                Ref(AWS_ACCOUNT_ID),
                ".dkr.ecr.",
                Ref(AWS_REGION),
                ".amazonaws.com/",
                Ref(repository),
                ":",
                app_revision,
            ]),
            PortMappings=[PortMapping(
                ContainerPort=web_worker_port,
                HostPort=web_worker_port,
            )],
            Environment=[
                Environment(
                    Name="AWS_STORAGE_BUCKET_NAME",
                    Value=Ref(assets_bucket),
                ),
            ],
        )
    ],
)


app_service_role = iam.Role(
    "AppServiceRole",
    template=template,
    AssumeRolePolicyDocument=dict(Statement=[dict(
        Effect="Allow",
        Principal=dict(Service=["ecs.amazonaws.com"]),
        Action=["sts:AssumeRole"],
    )]),
    Path="/",
    Policies=[
        iam.Policy(
            PolicyName="WebServicePolicy",
            PolicyDocument=dict(
                Statement=[dict(
                    Effect="Allow",
                    Action=[
                        "elasticloadbalancing:Describe*",
                        "elasticloadbalancing"
                        ":DeregisterInstancesFromLoadBalancer",
                        "elasticloadbalancing"
                        ":RegisterInstancesWithLoadBalancer",
                        "ec2:Describe*",
                        "ec2:AuthorizeSecurityGroupIngress",
                    ],
                    Resource="*",
                )],
            ),
        ),
    ]
)


app_service = Service(
    "AppService",
    template=template,
    Cluster=Ref(cluster),
    Condition=deploy_condition,
    DependsOn=[autoscaling_group_name],
    DesiredCount=web_worker_desired_count,
    LoadBalancers=[LoadBalancer(
        ContainerName="WebWorker",
        ContainerPort=web_worker_port,
        LoadBalancerName=Ref(load_balancer),
    )],
    TaskDefinition=Ref(web_task_definition),
    Role=Ref(app_service_role),
)
