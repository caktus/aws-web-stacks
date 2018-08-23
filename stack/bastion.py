import troposphere.ec2 as ec2
from troposphere import Equals, Join, Not, Output, Parameter, Ref, Tags

from .template import template
from .vpc import public_subnet, vpc

bastion_ami = template.add_parameter(
    Parameter(
        "BastionAMI",
        Description="(Optional) Bastion or VPN server AMI in the same region as this stack",
        Type="String",
        Default="",
    ),
    group="Bastion Server",
    label="Router AMI",
)

bastion_instance_type = template.add_parameter(
    Parameter(
        "BastionInstanceType",
        Description="(Optional) Instance type to use for bastion server.",
        Type="String",
        Default="t2.nano",
    ),
    group="Bastion Server",
    label="Instance Type",
)

bastion_key_name = template.add_parameter(
    Parameter(
        "BastionKeyName",
        Description="Name of an existing EC2 KeyPair to enable SSH access to "
                    "the Bastion instance.",
        Type="AWS::EC2::KeyPair::KeyName",
        ConstraintDescription="must be the name of an existing EC2 KeyPair."
    ),
    group="Bastion Server",
    label="SSH Key Name",
)

bastion_ami_set = "BastionAmiSet"
template.add_condition(bastion_ami_set, Not(Equals("", Ref(bastion_ami))))

bastion_security_group = ec2.SecurityGroup(
    'BastionSecurityGroup',
    template=template,
    GroupDescription="Bastion server security group (manually add your ingress "
                     "rules to this security group).",
    VpcId=Ref(vpc),
    Condition=bastion_ami_set,
)

# Elastic IP for Bastion instance
bastion_eip = template.add_resource(ec2.EIP("BastionEip"))

bastion_instance = ec2.Instance(
    "BastionInstance",
    template=template,
    ImageId=Ref(bastion_ami),
    InstanceType=Ref(bastion_instance_type),
    KeyName=Ref(bastion_key_name),
    SecurityGroupIds=[Ref(bastion_security_group)],
    SubnetId=Ref(public_subnet),
    Condition=bastion_ami_set,
    Tags=Tags(
        Name=Join("", [Ref("AWS::StackName"), "bastion"]),
    ),
)

# Associate the Elastic IP separately, so it doesn't change when the instance changes.
eip_assoc = template.add_resource(ec2.EIPAssociation(
    "BastionEipAssociation",
    InstanceId=Ref(bastion_instance),
    EIP=Ref(bastion_eip),
))

template.add_output([
    Output(
        "BastionIP",
        Description="Public IP address of Bastion instance",
        Value=Ref(bastion_eip),
    ),
])
