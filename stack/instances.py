from troposphere import (
    autoscaling,
    AWS_STACK_NAME,
    Equals,
    iam,
    Join,
    Parameter,
    Ref,
)


from .template import template
from .vpc import container_a_subnet, container_b_subnet
from .assets import assets_management_policy
from .common import container_instance_type
from .load_balancer import load_balancer, web_worker_health_check
from .logs import logging_policy
from .security_groups import container_security_group


ami = Ref(template.add_parameter(Parameter(
    "AMI",
    Description="The Amazon Machine Image (AMI) to use for instances. Make "
                "sure to use the correct AMI for your region and instance "
                "type (t2 instances require HVM AMIs).",
    Type="String",
    Default="",
)))


key_name = template.add_parameter(Parameter(
    "KeyName",
    Description="Name of an existing EC2 KeyPair to enable SSH access to "
                "the AWS EC2 instances",
    Type="AWS::EC2::KeyPair::KeyName",
    ConstraintDescription="must be the name of an existing EC2 KeyPair."
))


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
    Default="4",
)))


desired_container_instances = Ref(template.add_parameter(Parameter(
    "DesiredScale",
    Description="Desired container instances count",
    Type="Number",
    Default="2",
)))


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
    ]
)


# EC2 instance profile
container_instance_profile = iam.InstanceProfile(
    "ContainerInstanceProfile",
    template=template,
    Path="/",
    Roles=[Ref(container_instance_role)],
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
    KeyName=Ref(key_name),
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
    HealthCheckType="EC2",
    HealthCheckGracePeriod=300,
    Tags=[
        {
            "Key": "Name",
            "Value": Join("-", [Ref(AWS_STACK_NAME), "web_worker"]),
            "PropagateAtLaunch": True,
        }
    ],
)
