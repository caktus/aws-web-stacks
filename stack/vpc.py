from troposphere import Cidr, GetAtt, Join, Output, Ref, Select, Sub, Tag, Tags
from troposphere.ec2 import (
    EIP,
    VPC,
    EgressOnlyInternetGateway,
    InternetGateway,
    NatGateway,
    Route,
    RouteTable,
    Subnet,
    SubnetRouteTableAssociation,
    VPCCidrBlock,
    VPCEndpoint,
    VPCGatewayAttachment
)

from . import USE_NAT_GATEWAY
from .template import template
from .utils import ParameterWithDefaults as Parameter

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
        Description="VPC CIDR block.",
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
        Description="Public subnet A CIDR.",
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
        Description="Public subnet B CIDR.",
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
        Description="Private subnet A CIDR.",
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
        Description="Private subnet B CIDR.",
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

# Add an Amazon-provided IPv6 CIDR block to the VPC (dualstack)
# (AWS::EC2::VPC has no IPv6 properties of its own - use VPCCidrBlock)
vpc_ipv6_cidr = VPCCidrBlock(
    "VpcIpv6Cidr",
    template=template,
    VpcId=Ref(vpc),
    AmazonProvidedIpv6CidrBlock=True,
)

# Split the /56 Amazon-provided block into four /64s, one per subnet.
# Fn::Cidr's third argument is "cidrBits": 128 - 64 = 64 for /64 subnets.
v6_subnet_cidrs = Cidr(Select(0, GetAtt(vpc, "Ipv6CidrBlocks")), 4, 64)


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

# Egress-only IGW: gives private subnets outbound IPv6 without inbound exposure
egress_only_igw = EgressOnlyInternetGateway(
    "EgressOnlyIGW",
    template=template,
    VpcId=Ref(vpc),
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "eigw"]),
    ),
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

public_route_v6 = Route(
    "PublicRouteV6",
    template=template,
    GatewayId=Ref(internet_gateway),
    DestinationIpv6CidrBlock="::/0",
    RouteTableId=Ref(public_route_table),
)

# EKS subnet tags (always added since EKS is the only deployment mode)
public_subnet_eks_tags = [Tag("kubernetes.io/role/elb", "1")]
private_subnet_eks_tags = [Tag("kubernetes.io/role/internal-elb", "1")]

# Holds load balancer, NAT gateway, and bastion (if specified)
public_subnet_a = Subnet(
    "PublicSubnetA",
    template=template,
    DependsOn=["VpcIpv6Cidr"],
    VpcId=Ref(vpc),
    CidrBlock=Ref(public_subnet_a_cidr),
    Ipv6CidrBlock=Select(0, v6_subnet_cidrs),
    AvailabilityZone=Ref(primary_az),
    Tags=Tags(
        Tag("Name", Join("-", [Ref("AWS::StackName"), "public-a"])),
        *public_subnet_eks_tags,
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
    DependsOn=["VpcIpv6Cidr"],
    VpcId=Ref(vpc),
    CidrBlock=Ref(public_subnet_b_cidr),
    Ipv6CidrBlock=Select(1, v6_subnet_cidrs),
    AvailabilityZone=Ref(secondary_az),
    Tags=Tags(
        Tag("Name", Join("-", [Ref("AWS::StackName"), "public-b"])),
        *public_subnet_eks_tags,
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

    # NAT64: IPv6-only workloads reach IPv4 services via the NAT gateway
    private_nat64_route = Route(
        "NatGatewayRouteNat64",
        template=template,
        RouteTableId=Ref(nat_gateway_route_table),
        DestinationIpv6CidrBlock="64:ff9b::/96",
        NatGatewayId=Ref(nat_gateway),
    )

    # Outbound IPv6 for private subnets via the egress-only IGW
    private_igw_route_v6 = Route(
        "PrivateRouteV6",
        template=template,
        RouteTableId=Ref(nat_gateway_route_table),
        DestinationIpv6CidrBlock="::/0",
        EgressOnlyInternetGatewayId=Ref(egress_only_igw),
    )

    private_route_table = Ref(nat_gateway_route_table)

    # Add a VPC Endpoint for S3 so we can talk directly to S3
    # (without going through NAT gateway)
    VPCEndpoint(
        "VPCS3Endpoint",
        template=template,
        ServiceName=Sub("com.amazonaws.${AWS::Region}.s3"),
        VpcId=Ref(vpc),
        RouteTableIds=[private_route_table],
    )
else:
    private_route_table = Ref(public_route_table)


# Holds backend instances
private_subnet_a = Subnet(
    "PrivateSubnetA",
    template=template,
    DependsOn=["VpcIpv6Cidr"],
    VpcId=Ref(vpc),
    CidrBlock=Ref(private_subnet_a_cidr),
    Ipv6CidrBlock=Select(2, v6_subnet_cidrs),
    MapPublicIpOnLaunch=not USE_NAT_GATEWAY,
    AvailabilityZone=Ref(primary_az),
    Tags=Tags(
        Tag("Name", Join("-", [Ref("AWS::StackName"), "private-a"])),
        *private_subnet_eks_tags,
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
    DependsOn=["VpcIpv6Cidr"],
    VpcId=Ref(vpc),
    CidrBlock=Ref(private_subnet_b_cidr),
    Ipv6CidrBlock=Select(3, v6_subnet_cidrs),
    MapPublicIpOnLaunch=not USE_NAT_GATEWAY,
    AvailabilityZone=Ref(secondary_az),
    Tags=Tags(
        Tag("Name", Join("-", [Ref("AWS::StackName"), "private-b"])),
        *private_subnet_eks_tags,
    ),
)


SubnetRouteTableAssociation(
    "PrivateSubnetBRouteTableAssociation",
    template=template,
    SubnetId=Ref(private_subnet_b),
    RouteTableId=private_route_table,
)

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

template.add_output(Output(
    "VpcId",
    Description="VPC ID",
    Value=Ref(vpc),
))
template.add_output(Output(
    "PublicSubnetIds",
    Description="Public subnets.",
    Value=Join(",", [Ref(public_subnet_a), Ref(public_subnet_b)]),
))
template.add_output(Output(
    "PrivateSubnetIds",
    Description="Private subnets.",
    Value=Join(",", [Ref(private_subnet_a), Ref(private_subnet_b)]),
))
