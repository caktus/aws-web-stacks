import os

from troposphere import (
    AWS_STACK_NAME,
    Base64,
    Equals,
    GetAtt,
    If,
    Join,
    Not,
    Ref,
    Sub,
    autoscaling,
    eks,
    iam
)
from troposphere.policies import AutoScalingRollingUpdate

from .assets import assets_management_policy
from .common import container_instance_type, use_aes256_encryption
from .logs import logging_policy
from .security_groups import container_security_group
from .template import template
from .utils import ParameterWithDefaults as Parameter
from .vpc import private_subnet_a, private_subnet_b

USE_EKS = os.getenv("USE_EKS") == "on"

ami = Ref(template.add_parameter(
    Parameter(
        "AMI",
        Description="%sThe Amazon Machine Image (AMI) to use for instances. Make "
                    "sure to use the correct AMI for your region and instance "
                    "type (t2 instances require HVM AMIs)." % "(Optional) " if USE_EKS else "",
        Type="String",
        Default="",
    ),
    group="Application Server",
    label="Amazon Machine Image (AMI)",
))

if USE_EKS:
    ami_ssm = Ref(template.add_parameter(
        Parameter(
            "AMISSMParam",
            Description="AWS Systems Manager Parameter Store parameter of the "
                        "AMI ID for the worker node instances.",
            Type="AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>",
            Default="/aws/service/eks/optimized-ami/1.14/amazon-linux-2/recommended/image_id",
        ),
        group="Application Server",
        label="Amazon Machine Image (AMI)",
    ))
    ami_condition = "AMICondition"
    template.add_condition(
        ami_condition,
        Not(Equals(ami, "")),
    )
    ami = If(ami_condition, ami, ami_ssm)


key_name = template.add_parameter(
    Parameter(
        "KeyName",
        Description="Name of an existing EC2 KeyPair to enable SSH access to "
                    "the AWS EC2 instances",
        Type="AWS::EC2::KeyPair::KeyName",
        ConstraintDescription="must be the name of an existing EC2 KeyPair."
    ),
    group="Application Server",
    label="SSH Key Name",
)

desired_container_instances = Ref(template.add_parameter(
    Parameter(
        "DesiredScale",
        Description="Desired container instances count",
        Type="Number",
        Default="2",
    ),
    group="Application Server",
    label="Desired Instance Count",
))

max_container_instances = Ref(template.add_parameter(
    Parameter(
        "MaxScale",
        Description="Maximum container instances count",
        Type="Number",
        Default="4",
    ),
    group="Application Server",
    label="Maximum Instance Count",
))

container_volume_size = Ref(template.add_parameter(
    Parameter(
        "ContainerVolumeSize",
        Description="Size of instance EBS root volume (in GB)",
        Type="Number",
        Default="20",
    ),
    group="Application Server",
    label="Root Volume Size",
))

if not USE_EKS:
    from .load_balancer import web_worker_health_check
    tcp_health_check_condition = "TcpHealthCheck"
    template.add_condition(
        tcp_health_check_condition,
        Equals(web_worker_health_check, ""),
    )

# EC2 instance role
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
        assets_management_policy,
        logging_policy,
    ],
    **(
        dict(
            ManagedPolicyArns=[
                "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
                "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
                "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
            ]
        )
        if USE_EKS
        else {}
    )
)

# EC2 instance profile
container_instance_profile = iam.InstanceProfile(
    "ContainerInstanceProfile",
    template=template,
    Path="/",
    Roles=[Ref(container_instance_role)],
)

if USE_EKS:
    from .security_groups import eks_security_group

    eks_service_role = iam.Role(
        "EksServiceRole",
        template=template,
        AssumeRolePolicyDocument=dict(Statement=[dict(
            Effect="Allow",
            Principal=dict(Service=["eks.amazonaws.com"]),
            Action=["sts:AssumeRole"],
        )]),
        Path="/",
        ManagedPolicyArns=[
            "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
            "arn:aws:iam::aws:policy/AmazonEKSServicePolicy",
        ]
    )

    cluster = eks.Cluster(
        "EksCluster",
        template=template,
        ResourcesVpcConfig=eks.ResourcesVpcConfig(
            SubnetIds=[
                Ref(private_subnet_a),
                Ref(private_subnet_b),
            ],
            SecurityGroupIds=[
                Ref(eks_security_group),
            ]
        ),
        RoleArn=GetAtt(eks_service_role, "Arn"),
    )

instance_configuration_name = "LaunchConfiguration"

autoscaling_group_name = "AutoScalingGroup"

container_instance_configuration = autoscaling.LaunchConfiguration(
    instance_configuration_name,
    template=template,
    SecurityGroups=[Ref(container_security_group)],
    InstanceType=container_instance_type,
    ImageId=ami,
    IamInstanceProfile=Ref(container_instance_profile),
    BlockDeviceMappings=[
        autoscaling.BlockDeviceMapping(
            DeviceName="/dev/sda1",
            Ebs=autoscaling.EBSBlockDevice(
                VolumeType="gp2",
                VolumeSize=container_volume_size,
                Encrypted=use_aes256_encryption,
            )
        ),
    ],
    KeyName=Ref(key_name),
    **(
        dict(
            UserData=Base64(
                Sub(
                    "#!/bin/bash\n"
                    "set -o xtrace\n"
                    "/etc/eks/bootstrap.sh ${EksCluster}\n"
                    "/opt/aws/bin/cfn-signal --exit-code $?"
                    "    --stack  ${AWS::StackName}"
                    "    --resource NodeGroup"
                    "    --region ${AWS::Region}"
                )
            )
        )
        if USE_EKS
        else {}
    )
)

autoscaling_group_extra = {}
autoscaling_group_tags = []
if not USE_EKS:
    from .load_balancer import load_balancer
    autoscaling_group_extra["LoadBalancerNames"] = [Ref(load_balancer)]
else:
    # TBD: We might want to make this UpdatePolicy standard, but applying
    # only for EKS since it may change behavior for existing stacks.
    autoscaling_group_extra["UpdatePolicy"] = AutoScalingRollingUpdate(
        MaxBatchSize=1,
        MinInstancesInService=desired_container_instances,
        PauseTime="PT5M",
    )
    autoscaling_group_tags.append(
        {
            "Key": Sub("kubernetes.io/cluster/${EksCluster}"),
            "Value": "owned",
            "PropagateAtLaunch": True,
        }
    )

autoscaling_group = autoscaling.AutoScalingGroup(
    autoscaling_group_name,
    template=template,
    VPCZoneIdentifier=[Ref(private_subnet_a), Ref(private_subnet_b)],
    MinSize=desired_container_instances,
    MaxSize=max_container_instances,
    DesiredCapacity=desired_container_instances,
    LaunchConfigurationName=Ref(container_instance_configuration),
    HealthCheckType="EC2",
    HealthCheckGracePeriod=300,
    Tags=[
        {
            "Key": "Name",
            "Value": Join("-", [Ref(AWS_STACK_NAME), "web_worker"]),
            "PropagateAtLaunch": True,
        },
        {
            "Key": "aws-web-stacks:role",
            "Value": "worker",
            "PropagateAtLaunch": True,
        },
        *autoscaling_group_tags,
    ],
    **autoscaling_group_extra,
)
