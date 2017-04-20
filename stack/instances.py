from troposphere import (
    autoscaling,
    AWS_STACK_NAME,
    elasticloadbalancing as elb,
    Equals,
    GetAtt,
    iam,
    If,
    Join,
    Output,
    Parameter,
    Ref,
)


from .template import template
from .vpc import (
    loadbalancer_a_subnet,
    loadbalancer_b_subnet,
    container_a_subnet,
    container_b_subnet,
)
from .assets import assets_management_policy
from .common import container_instance_type
from .logs import logging_policy
from .security_groups import (
    load_balancer_security_group,
    container_security_group,
)


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


web_worker_port = Ref(template.add_parameter(Parameter(
    "WebWorkerPort",
    Description="Default web worker exposed port (non-HTTPS)",
    Type="Number",
    Default="80",
)))


web_worker_desired_count = Ref(template.add_parameter(Parameter(
    "WebWorkerDesiredCount",
    Description="Web worker task instance count",
    Type="Number",
    Default="2",
)))


web_worker_protocol = Ref(template.add_parameter(Parameter(
    "WebWorkerProtocol",
    Description="Web worker instance protocol",
    Type="String",
    Default="HTTP",
    AllowedValues=["HTTP", "HTTPS"],
)))


web_worker_health_check = Ref(template.add_parameter(Parameter(
    "WebWorkerHealthCheck",
    Description="Web worker health check URL path, e.g., \"/health-check\"; "
                "will default to TCP-only health check if left blank",
    Type="String",
    Default="",
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


# Web load balancer

load_balancer = elb.LoadBalancer(
    'LoadBalancer',
    template=template,
    Subnets=[
        Ref(loadbalancer_a_subnet),
        Ref(loadbalancer_b_subnet),
    ],
    SecurityGroups=[Ref(load_balancer_security_group)],
    Listeners=[
        elb.Listener(
            LoadBalancerPort=80,
            InstanceProtocol=web_worker_protocol,
            InstancePort=web_worker_port,
            Protocol='HTTP',
        ),
        # configure the default HTTPS listener to pass TCP traffic directly,
        # since GovCloud doesn't support the Certificate Manager (this can be
        # modified to enable SSL termination at the load balancer via the AWS
        # console, if needed)
        elb.Listener(
            LoadBalancerPort=443,
            InstanceProtocol='TCP',
            InstancePort=443,
            Protocol='TCP',
        ),
    ],
    HealthCheck=elb.HealthCheck(
        Target=If(
            tcp_health_check_condition,
            Join("", ["TCP:", web_worker_port]),
            Join("", [
                web_worker_protocol,
                ":",
                web_worker_port,
                web_worker_health_check,
            ]),
        ),
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
