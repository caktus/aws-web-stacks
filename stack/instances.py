from troposphere import (
    AWS_STACK_NAME,
    Base64,
    Equals,
    Join,
    Ref,
    Sub,
    autoscaling,
)

from .common import use_aes256_encryption
from .containers import desired_container_instances, max_container_instances, container_volume_size, \
    container_instance_profile, container_instance_type
from .load_balancer import load_balancer, web_worker_health_check
from .security_groups import container_security_group
from .template import template
from .utils import ParameterWithDefaults as Parameter
from .vpc import private_subnet_a, private_subnet_b

ami = Ref(
    template.add_parameter(
        Parameter(
            "AMI",
            Description="The Amazon Machine Image (AMI) to use for instances. Make "
            "sure to use the correct AMI for your region and instance "
            "type (t2 instances require HVM AMIs).",
            Type="String",
            Default="",
        ),
        group="Application Server",
        label="Amazon Machine Image (AMI)",
    )
)


key_name = template.add_parameter(
    Parameter(
        "KeyName",
        Description="Name of an existing EC2 KeyPair to enable SSH access to "
        "the AWS EC2 instances",
        Type="AWS::EC2::KeyPair::KeyName",
        ConstraintDescription="must be the name of an existing EC2 KeyPair.",
    ),
    group="Application Server",
    label="SSH Key Name",
)

tcp_health_check_condition = "TcpHealthCheck"
template.add_condition(
    tcp_health_check_condition, Equals(web_worker_health_check, ""),
)

# EC2 instance role

# EC2 instance profile

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
            ),
        ),
    ],
    KeyName=Ref(key_name),
)

autoscaling_group_extra = {}
autoscaling_group_tags = []

autoscaling_group_extra["LoadBalancerNames"] = [Ref(load_balancer)]

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
        {"Key": "aws-web-stacks:role", "Value": "worker", "PropagateAtLaunch": True,},
        *autoscaling_group_tags,
    ],
    **autoscaling_group_extra,
)
