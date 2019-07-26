import os

from troposphere import GetAtt, Join, Ref, Tags
from troposphere.ec2 import (
    EIP,
    VPC,
    InternetGateway,
    NatGateway,
    Route,
    RouteTable,
    Subnet,
    SubnetRouteTableAssociation,
    VPCGatewayAttachment
)

from .template import template
from .utils import ParameterWithDefaults as Parameter

USE_NAT_GATEWAY = os.environ.get('USE_NAT_GATEWAY') == 'on'
USE_DOKKU = os.environ.get('USE_DOKKU') == 'on'


primary_az = template.add_parameter(
    Parameter(
        "PrimaryAZ",
        Description="The primary availability zone for creating resources.",
        Type="AWS::EC2::AvailabilityZone::Name",
    ),
    group="Global",
    label="Primary Availability Zone",
)


secondary_az = template.add_parameter(
    Parameter(
        "SecondaryAZ",
        Description="The secondary availability zone for creating resources. Must differ from primary zone.",
        Type="AWS::EC2::AvailabilityZone::Name",
    ),
    group="Global",
    label="Secondary Availability Zone",
)


vpc = VPC(
    "Vpc",
    template=template,
    CidrBlock="10.0.0.0/16",
    EnableDnsSupport=True,
    EnableDnsHostnames=True,
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "vpc"]),
    ),
)


# Allow outgoing to outside VPC
internet_gateway = InternetGateway(
    "InternetGateway",
    template=template,
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "igw"]),
    ),
)


# Attach Gateway to VPC
VPCGatewayAttachment(
    "GatewayAttachement",
    template=template,
    VpcId=Ref(vpc),
    InternetGatewayId=Ref(internet_gateway),
)


# Public route table
public_route_table = RouteTable(
    "PublicRouteTable",
    template=template,
    VpcId=Ref(vpc),
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "public"]),
    ),
)


public_route = Route(
    "PublicRoute",
    template=template,
    GatewayId=Ref(internet_gateway),
    DestinationCidrBlock="0.0.0.0/0",
    RouteTableId=Ref(public_route_table),
)


# Holds public instances
public_subnet_cidr = "10.0.1.0/24"

public_subnet = Subnet(
    "PublicSubnet",
    template=template,
    VpcId=Ref(vpc),
    CidrBlock=public_subnet_cidr,
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "public"]),
    ),
)


SubnetRouteTableAssociation(
    "PublicSubnetRouteTableAssociation",
    template=template,
    RouteTableId=Ref(public_route_table),
    SubnetId=Ref(public_subnet),
)

if USE_NAT_GATEWAY:
    # NAT
    nat_ip = EIP(
        "NatIp",
        template=template,
        Domain="vpc",
    )

    nat_gateway = NatGateway(
        "NatGateway",
        template=template,
        AllocationId=GetAtt(nat_ip, "AllocationId"),
        SubnetId=Ref(public_subnet),
        Tags=Tags(
            Name=Join("-", [Ref("AWS::StackName"), "nat"]),
        ),
    )


if not USE_DOKKU:
    # Holds load balancer
    loadbalancer_a_subnet_cidr = "10.0.2.0/24"
    loadbalancer_a_subnet = Subnet(
        "LoadbalancerASubnet",
        template=template,
        VpcId=Ref(vpc),
        CidrBlock=loadbalancer_a_subnet_cidr,
        AvailabilityZone=Ref(primary_az),
        Tags=Tags(
            Name=Join("-", [Ref("AWS::StackName"), "elb-a"]),
        ),
    )

    SubnetRouteTableAssociation(
        "LoadbalancerASubnetRouteTableAssociation",
        template=template,
        RouteTableId=Ref(public_route_table),
        SubnetId=Ref(loadbalancer_a_subnet),
    )

    loadbalancer_b_subnet_cidr = "10.0.3.0/24"
    loadbalancer_b_subnet = Subnet(
        "LoadbalancerBSubnet",
        template=template,
        VpcId=Ref(vpc),
        CidrBlock=loadbalancer_b_subnet_cidr,
        AvailabilityZone=Ref(secondary_az),
        Tags=Tags(
            Name=Join("-", [Ref("AWS::StackName"), "elb-b"]),
        ),
    )

    SubnetRouteTableAssociation(
        "LoadbalancerBSubnetRouteTableAssociation",
        template=template,
        RouteTableId=Ref(public_route_table),
        SubnetId=Ref(loadbalancer_b_subnet),
    )


if USE_NAT_GATEWAY:
    # Private route table
    private_route_table = RouteTable(
        "PrivateRouteTable",
        template=template,
        VpcId=Ref(vpc),
        Tags=Tags(
            Name=Join("-", [Ref("AWS::StackName"), "private"]),
        ),
    )

    private_nat_route = Route(
        "PrivateNatRoute",
        template=template,
        RouteTableId=Ref(private_route_table),
        DestinationCidrBlock="0.0.0.0/0",
        NatGatewayId=Ref(nat_gateway),
    )


# Holds containers instances
container_a_subnet_cidr = "10.0.10.0/24"
container_a_subnet = Subnet(
    "ContainerASubnet",
    template=template,
    VpcId=Ref(vpc),
    CidrBlock=container_a_subnet_cidr,
    MapPublicIpOnLaunch=not USE_NAT_GATEWAY,
    AvailabilityZone=Ref(primary_az),
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "container-a"]),
    ),
)


container_route_table = Ref(private_route_table) if USE_NAT_GATEWAY\
    else Ref(public_route_table)


SubnetRouteTableAssociation(
    "ContainerARouteTableAssociation",
    template=template,
    SubnetId=Ref(container_a_subnet),
    RouteTableId=container_route_table,
)


container_b_subnet_cidr = "10.0.11.0/24"
container_b_subnet = Subnet(
    "ContainerBSubnet",
    template=template,
    VpcId=Ref(vpc),
    CidrBlock=container_b_subnet_cidr,
    MapPublicIpOnLaunch=not USE_NAT_GATEWAY,
    AvailabilityZone=Ref(secondary_az),
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "container-b"]),
    ),
)


SubnetRouteTableAssociation(
    "ContainerBRouteTableAssociation",
    template=template,
    SubnetId=Ref(container_b_subnet),
    RouteTableId=container_route_table,
)
