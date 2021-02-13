from troposphere import (
    Cidr,
    FindInMap,
    GetAtt,
    Join,
    Ref,
    Select,
    Sub,
    Tag,
    Tags
)
from troposphere.ec2 import (
    EIP,
    VPC,
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

from . import USE_EKS, USE_NAT_GATEWAY
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
        Description="The primary IPv4 CIDR block for the VPC. Must contain at least "
                    "four (4) of the block size specified in IPv4 Subnet Size. "
                    "[Possibly not modifiable after stack creation]",
        Type="String",
        Default="10.0.0.0/20",
        AllowedPattern=PRIVATE_IPV4_CIDR_REGEX,
        ConstraintDescription=PRIVATE_IPV4_CONSTRAINT,
    ),
    group="Global",
    label="VPC IPv4 CIDR Block",
)

subnet_size_map_name = "SubnetSizeMap"
subnet_size_map = {
    # Allow for creation of /29 -> /16 (including everything in between)
    f"slash-{32-bits}": {"Bits": str(bits)} for bits in range(3, 17)
}
template.add_mapping(subnet_size_map_name, subnet_size_map)

subnet_size = template.add_parameter(
    Parameter(
        "VpcSubnetSize",
        Description="IPv4 CIDR block size for all subnets. "
                    "Forward slashes (/) aren't supported in CloudFormation mappings, "
                    "so these are described as \"slash-N\" instead.",
        Type="String",
        AllowedValues=list(subnet_size_map.keys()),
        Default="slash-22",
    ),
    group="Global",
    label="IPv4 Subnet Size",
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

# Attach Amazon-provided IPv6 block
ipv6_block = VPCCidrBlock(
    "IPv6CidrBlock",
    template=template,
    AmazonProvidedIpv6CidrBlock=True,
    VpcId=Ref(vpc),
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


ipv6_public_route = Route(
    "Ipv6PublicRoute",
    template=template,
    GatewayId=Ref(internet_gateway),
    DestinationIpv6CidrBlock="::/0",
    RouteTableId=Ref(public_route_table),
)


public_subnet_eks_tags = []
private_subnet_eks_tags = []
if USE_EKS:
    public_subnet_eks_tags.append(Tag("kubernetes.io/role/elb", "1"))
    # Tag your private subnets so that Kubernetes knows that it can use them for internal load balancers.
    private_subnet_eks_tags.append(Tag("kubernetes.io/role/internal-elb", "1"))


ipv4_subnets = Cidr(Ref(vpc_cidr), 4, FindInMap(subnet_size_map_name, Ref(subnet_size), "Bits"))

# Per the docs, AmazonProvidedIpv6CidrBlock gives us a /56, which contains 256 /64 subnets
# https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-vpccidrblock.html
# ipv6_subnets = Cidr(Select(0, GetAtt(vpc, "Ipv6CidrBlocks")), 256, "64")

PUBLIC_SUBNET_A_CIDR_IDX = 0
PUBLIC_SUBNET_B_CIDR_IDX = 1
PRIVATE_SUBNET_A_CIDR_IDX = 2
PRIVATE_SUBNET_B_CIDR_IDX = 3

# Holds load balancer, NAT gateway, and bastion (if specified)
public_subnet_a = Subnet(
    "PublicSubnetA",
    template=template,
    VpcId=Ref(vpc),
    CidrBlock=Select(PUBLIC_SUBNET_A_CIDR_IDX, ipv4_subnets),
    # Ipv6CidrBlock=Select(PUBLIC_SUBNET_A_CIDR_IDX, ipv6_subnets),
    # AssignIpv6AddressOnCreation=True,
    AvailabilityZone=Ref(primary_az),
    # Ensure IPv6 /56 is assigned before attempting to use it
    DependsOn=ipv6_block,
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
    VpcId=Ref(vpc),
    CidrBlock=Select(PUBLIC_SUBNET_B_CIDR_IDX, ipv4_subnets),
    # Ipv6CidrBlock=Select(PUBLIC_SUBNET_B_CIDR_IDX, ipv6_subnets),
    # AssignIpv6AddressOnCreation=True,
    AvailabilityZone=Ref(secondary_az),
    # Ensure IPv6 /56 is assigned before attempting to use it
    DependsOn=ipv6_block,
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
private_subnet_a_cidr = Select(PRIVATE_SUBNET_A_CIDR_IDX, ipv4_subnets)
private_subnet_a = Subnet(
    "PrivateSubnetA",
    template=template,
    VpcId=Ref(vpc),
    CidrBlock=private_subnet_a_cidr,
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


private_subnet_b_cidr = Select(PRIVATE_SUBNET_B_CIDR_IDX, ipv4_subnets)
private_subnet_b = Subnet(
    "PrivateSubnetB",
    template=template,
    VpcId=Ref(vpc),
    CidrBlock=private_subnet_b_cidr,
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
