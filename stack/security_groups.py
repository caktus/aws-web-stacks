import os

from troposphere import Join, Ref, Sub, Tag, Tags
from troposphere.ec2 import (
    SecurityGroup,
    SecurityGroupEgress,
    SecurityGroupIngress,
    SecurityGroupRule
)

from .common import administrator_ip_address
from .template import template
from .vpc import vpc

USE_EKS = os.getenv("USE_EKS") == "on"

ingress_rules = []

if not USE_EKS:
    # EKS manages its own ELBs, so this stack doesn't have one
    load_balancer_security_group = SecurityGroup(
        "LoadBalancerSecurityGroup",
        template=template,
        GroupDescription="Web load balancer security group.",
        VpcId=Ref(vpc),
        SecurityGroupIngress=[
            # allow incoming traffic from the public internet to the load balancer
            # on ports 80 and 443
            SecurityGroupRule(
                IpProtocol="tcp",
                FromPort=port,
                ToPort=port,
                CidrIp="0.0.0.0/0",
            ) for port in ["80", "443"]
        ],
        Tags=Tags(
            Name=Join("-", [Ref("AWS::StackName"), "elb"]),
        ),
    )

    # allow traffic from the load balancer subnets to the web workers
    if os.environ.get('USE_ECS') == 'on' or os.environ.get('USE_EC2') == 'on':
        # if using ECS or EC2, allow traffic to the configured WebWorkerPort
        web_worker_ports = [Ref("WebWorkerPort")]
    elif os.environ.get('USE_GOVCLOUD') == 'on':
        # if using GovCloud (real EC2 instances), allow traffic to the configured
        # WebWorkerPort and port 443
        web_worker_ports = [Ref("WebWorkerPort"), "443"]
    else:
        # otherwise, if using Elastic Beanstalk, allow traffic only to EB's default
        # web worker port (80)
        web_worker_ports = ["80"]

    # HTTP from web load balancer
    ingress_rules += [SecurityGroupRule(
        IpProtocol="tcp",
        FromPort=port,
        ToPort=port,
        SourceSecurityGroupId=Ref(load_balancer_security_group),
    ) for port in web_worker_ports]

    # Health check
    if os.environ.get('USE_EB') != 'on':
        ingress_rules.append(SecurityGroupRule(
            IpProtocol="tcp",
            FromPort=Ref("WebWorkerHealthCheckPort"),
            ToPort=Ref("WebWorkerHealthCheckPort"),
            Description="ELB Health Check",  # SecurityGroupRule doesn't support a Description attribute
            SourceSecurityGroupId=Ref(load_balancer_security_group),
        ))

if os.environ.get('USE_NAT_GATEWAY') != 'on':
    # Allow direct administrator access via SSH.
    ingress_rules.append(SecurityGroupRule(
        IpProtocol="tcp",
        FromPort="22",
        ToPort="22",
        Description="Administrator SSH Access",
        CidrIp=administrator_ip_address,
    ))

container_security_group = SecurityGroup(
    'ContainerSecurityGroup',
    template=template,
    GroupDescription="Container security group.",
    VpcId=Ref(vpc),
    SecurityGroupIngress=ingress_rules,
    Tags=Tags(
        *(
            [Tag(Sub("kubernetes.io/cluster/${EksCluster}"), "owned")]
            if USE_EKS
            else []
        ),
        Name=Join("-", [Ref("AWS::StackName"), "container"]),
    ),
)

if USE_EKS:
    eks_security_group = SecurityGroup(
        'EksClusterSecurityGroup',
        template=template,
        GroupDescription="EKS control plane security group.",
        VpcId=Ref(vpc),
        Tags=Tags(
            Name=Join("-", [Ref("AWS::StackName"), "eks-cluster"]),
        ),
    )

    # Security group rules adapted from:
    # https://amazon-eks.s3-us-west-2.amazonaws.com/cloudformation/2019-10-08/amazon-eks-nodegroup.yaml
    SecurityGroupIngress(
        'EksNodeSecurityGroupIngress',
        template=template,
        Description="Allow node to communicate with each other",
        GroupId=Ref(container_security_group),
        SourceSecurityGroupId=Ref(container_security_group),
        FromPort=0,
        ToPort=65535,
        IpProtocol="-1",
    )

    SecurityGroupIngress(
        'ClusterControlPlaneSecurityGroupIngress',
        template=template,
        Description="Allow pods to communicate with the cluster API Server",
        GroupId=Ref(eks_security_group),
        SourceSecurityGroupId=Ref(container_security_group),
        FromPort=443,
        ToPort=443,
        IpProtocol="tcp",
    )

    SecurityGroupEgress(
        "ControlPlaneEgressToNodeSecurityGroup",
        template=template,
        Description="Allow the cluster control plane to communicate with worker Kubelet and pods",
        DestinationSecurityGroupId=Ref(container_security_group),
        GroupId=Ref(eks_security_group),
        FromPort=1025,
        ToPort=65535,
        IpProtocol="tcp",
    )

    SecurityGroupEgress(
        "ControlPlaneEgressToNodeSecurityGroupOn443",
        template=template,
        Description="Allow the cluster control plane to communicate with pods "
                    "running extension API servers on port 443",
        DestinationSecurityGroupId=Ref(container_security_group),
        GroupId=Ref(eks_security_group),
        FromPort=443,
        ToPort=443,
        IpProtocol="tcp",
    )

    SecurityGroupIngress(
        "NodeSecurityGroupFromControlPlaneIngress",
        template=template,
        Description="Allow worker Kubelets and pods to receive communication from the cluster control plane",
        GroupId=Ref(container_security_group),
        SourceSecurityGroupId=Ref(eks_security_group),
        FromPort=1025,
        ToPort=65535,
        IpProtocol="tcp",
    )

    SecurityGroupIngress(
        "NodeSecurityGroupFromControlPlaneOn443Ingress",
        template=template,
        Description="Allow pods running extension API servers on port 443 "
                    "to receive communication from cluster control plane",
        GroupId=Ref(container_security_group),
        SourceSecurityGroupId=Ref(eks_security_group),
        FromPort=443,
        ToPort=443,
        IpProtocol="tcp",
    )
