import os

from troposphere import GetAtt, Join, Ref, Tag, Tags
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

# Allows for private IPv4 ranges in the 10.0.0.0/8, 172.16.0.0/12 and 192.168.0.0/16
# address spaces, with block size between /16 and /28 as allowed by VPCs and subnets.
PRIVATE_IPV4_CIDR_REGEX = r"^((10\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.)|(172\.(1[6-9]|2[0-9]|3[0-1])\.)|192\.168\.)(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.)([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\/(1[6-9]|2[0-8]))$"  # noqa: E501
PRIVATE_IPV4_CONSTRAINT = "Must be a private IPv4 range with size /16 and /28."

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

vpc_cidr = template.add_parameter(
    Parameter(
        "VpcCidr",
        Description="The primary IPv4 CIDR block for the VPC. "
                    "[Possibly not modifiable after stack creation]",
        Type="String",
        Default="10.0.0.0/20",
        AllowedPattern=PRIVATE_IPV4_CIDR_REGEX,
        ConstraintDescription=PRIVATE_IPV4_CONSTRAINT,
    ),
    group="Global",
    label="VPC IPv4 CIDR Block",
)

public_subnet_a_cidr = template.add_parameter(
    Parameter(
        "PublicSubnetACidr",
        Description="IPv4 CIDR block for the public subnet in the primary AZ. "
                    "[Possibly not modifiable after stack creation]",
        Type="String",
        Default="10.0.0.0/22",
        AllowedPattern=PRIVATE_IPV4_CIDR_REGEX,
        ConstraintDescription=PRIVATE_IPV4_CONSTRAINT,
    ),
    group="Global",
    label="Public Subnet A CIDR Block",
)

public_subnet_b_cidr = template.add_parameter(
    Parameter(
        "PublicSubnetBCidr",
        Description="IPv4 CIDR block for the public subnet in the secondary AZ. "
                    "[Possibly not modifiable after stack creation]",
        Type="String",
        Default="10.0.4.0/22",
        AllowedPattern=PRIVATE_IPV4_CIDR_REGEX,
        ConstraintDescription=PRIVATE_IPV4_CONSTRAINT,
    ),
    group="Global",
    label="Public Subnet B CIDR Block",
)

private_subnet_a_cidr = template.add_parameter(
    Parameter(
        "PrivateSubnetACidr",
        Description="IPv4 CIDR block for the private subnet in the primary AZ. "
                    "[Possibly not modifiable after stack creation]",
        Type="String",
        Default="10.0.8.0/22",
        AllowedPattern=PRIVATE_IPV4_CIDR_REGEX,
        ConstraintDescription=PRIVATE_IPV4_CONSTRAINT,
    ),
    group="Global",
    label="Private Subnet A CIDR Block",
)

private_subnet_b_cidr = template.add_parameter(
    Parameter(
        "PrivateSubnetBCidr",
        Description="IPv4 CIDR block for the private subnet in the secondary AZ. "
                    "[Possibly not modifiable after stack creation]",
        Type="String",
        Default="10.0.12.0/22",
        AllowedPattern=PRIVATE_IPV4_CIDR_REGEX,
        ConstraintDescription=PRIVATE_IPV4_CONSTRAINT,
    ),
    group="Global",
    label="Private Subnet B CIDR Block",
)


vpc = VPC(
    "Vpc",
    template=template,
    CidrBlock=Ref(vpc_cidr),
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

public_subnet_eks_tags = []
private_subnet_eks_tags = []
if os.getenv('USE_EKS') == 'on':
    public_subnet_eks_tags.append(Tag('kubernetes.io/role/elb', '1'))
    private_subnet_eks_tags.append(Tag('kubernetes.io/role/internal-elb', '1'))

# Holds load balancer, NAT gateway, and bastion (if specified)
public_subnet_a = Subnet(
    "PublicSubnetA",
    template=template,
    VpcId=Ref(vpc),
    CidrBlock=Ref(public_subnet_a_cidr),
    AvailabilityZone=Ref(primary_az),
    Tags=Tags(
        *public_subnet_eks_tags,
        Name=Join("-", [Ref("AWS::StackName"), "public-a"]),
    ),
)

SubnetRouteTableAssociation(
    "PublicSubnetARouteTableAssociation",
    template=template,
    RouteTableId=Ref(public_route_table),
    SubnetId=Ref(public_subnet_a),
)

public_subnet_b = Subnet(
    "PublicSubnetB",
    template=template,
    VpcId=Ref(vpc),
    CidrBlock=Ref(public_subnet_b_cidr),
    AvailabilityZone=Ref(secondary_az),
    Tags=Tags(
        *public_subnet_eks_tags,
        Name=Join("-", [Ref("AWS::StackName"), "public-b"]),
    ),
)

SubnetRouteTableAssociation(
    "PublicSubnetBRouteTableAssociation",
    template=template,
    RouteTableId=Ref(public_route_table),
    SubnetId=Ref(public_subnet_b),
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
        SubnetId=Ref(public_subnet_a),
        Tags=Tags(
            Name=Join("-", [Ref("AWS::StackName"), "nat"]),
        ),
    )

    # Private route table
    nat_gateway_route_table = RouteTable(
        "NatGatewayRouteTable",
        template=template,
        VpcId=Ref(vpc),
        Tags=Tags(
            Name=Join("-", [Ref("AWS::StackName"), "private"]),
        ),
    )

    private_nat_route = Route(
        "NatGatewayRoute",
        template=template,
        RouteTableId=Ref(nat_gateway_route_table),
        DestinationCidrBlock="0.0.0.0/0",
        NatGatewayId=Ref(nat_gateway),
    )

    private_route_table = Ref(nat_gateway_route_table)
else:
    private_route_table = Ref(public_route_table)


# Holds backend instances
private_subnet_a = Subnet(
    "PrivateSubnetA",
    template=template,
    VpcId=Ref(vpc),
    CidrBlock=Ref(private_subnet_a_cidr),
    MapPublicIpOnLaunch=not USE_NAT_GATEWAY,
    AvailabilityZone=Ref(primary_az),
    Tags=Tags(
        *private_subnet_eks_tags,
        Name=Join("-", [Ref("AWS::StackName"), "private-a"]),
    ),
)


SubnetRouteTableAssociation(
    "PrivateSubnetARouteTableAssociation",
    template=template,
    SubnetId=Ref(private_subnet_a),
    RouteTableId=private_route_table,
)


private_subnet_b = Subnet(
    "PrivateSubnetB",
    template=template,
    VpcId=Ref(vpc),
    CidrBlock=Ref(private_subnet_b_cidr),
    MapPublicIpOnLaunch=not USE_NAT_GATEWAY,
    AvailabilityZone=Ref(secondary_az),
    Tags=Tags(
        *private_subnet_eks_tags,
        Name=Join("-", [Ref("AWS::StackName"), "private-b"]),
    ),
)


SubnetRouteTableAssociation(
    "PrivateSubnetBRouteTableAssociation",
    template=template,
    SubnetId=Ref(private_subnet_b),
    RouteTableId=private_route_table,
)
