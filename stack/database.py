from troposphere import (
    ec2,
    rds,
    Ref,
    AWS_STACK_NAME,
)

from .template import template
from .vpc import (
    vpc,
    container_a_subnet,
    container_a_subnet_cidr,
    container_b_subnet,
    container_b_subnet_cidr,
)


db_security_group = ec2.SecurityGroup(
    'DatabaseSecurityGroup',
    template=template,
    GroupDescription="Database security group.",
    VpcId=Ref(vpc),
    SecurityGroupIngress=[
        # Postgres in from web clusters
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="5432",
            ToPort="5432",
            CidrIp=container_a_subnet_cidr,
        ),
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="5432",
            ToPort="5432",
            CidrIp=container_b_subnet_cidr,
        ),
    ],
)


db_subnet_group = rds.DBSubnetGroup(
    "DatabaseSubnetGroup",
    template=template,
    DBSubnetGroupDescription="Subnets available for the RDS DB Instance",
    SubnetIds=[Ref(container_a_subnet), Ref(container_b_subnet)],
)


db_instance = rds.DBInstance(
    "PostgreSQL",
    template=template,
    DBInstanceIdentifier=Ref(AWS_STACK_NAME),
    Engine="postgres",
    EngineVersion="9.4.5",
    MultiAZ=True,
    StorageType="gp2",
    DBSubnetGroupName=Ref(db_subnet_group),
    VPCSecurityGroups=[Ref(db_security_group)],
    BackupRetentionPeriod="7",
)
