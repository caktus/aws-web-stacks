from troposphere import (
    ec2,
    Parameter,
    rds,
    Ref,
)

from .template import template
from .vpc import (
    vpc,
    container_a_subnet,
    container_a_subnet_cidr,
    container_b_subnet,
    container_b_subnet_cidr,
)


db_name = template.add_parameter(Parameter(
    "DatabaseName",
    Default="app",
    Description="The database name",
    Type="String",
    MinLength="1",
    MaxLength="64",
    AllowedPattern="[a-zA-Z][a-zA-Z0-9]*",
    ConstraintDescription=(
        "must begin with a letter and contain only"
        " alphanumeric characters."
    )
))


db_user = template.add_parameter(Parameter(
    "DatabaseUser",
    Default="app",
    Description="The database admin account username",
    Type="String",
    MinLength="1",
    MaxLength="16",
    AllowedPattern="[a-zA-Z][a-zA-Z0-9]*",
    ConstraintDescription=(
        "must begin with a letter and contain only"
        " alphanumeric characters."
    )
))


db_password = template.add_parameter(Parameter(
    "DatabasePassword",
    NoEcho=True,
    Description="The database admin account password",
    Type="String",
    MinLength="10",
    MaxLength="41",
    AllowedPattern="[a-zA-Z0-9]*",
    ConstraintDescription="must consist of 10-41 alphanumeric characters."
))


db_class = template.add_parameter(Parameter(
    "DatabaseClass",
    Default="db.t2.micro",
    Description="Database instance class",
    Type="String",
    AllowedValues=[
        'db.t1.micro',
        'db.m1.small',
        'db.m4.large',
        'db.m4.xlarge',
        'db.m4.2xlarge',
        'db.m4.4xlarge',
        'db.m4.10xlarge',
        'db.r3.large',
        'db.r3.xlarge',
        'db.r3.2xlarge',
        'db.r3.4xlarge',
        'db.r3.8xlarge',
        'db.t2.micro',
        'db.t2.small',
        'db.t2.medium',
        'db.t2.large',
        'db.m3.medium',
        'db.m3.large',
        'db.m3.xlarge',
        'db.m3.2xlarge',
        'db.m1.small',
        'db.m1.medium',
        'db.m1.large',
        'db.m1.xlarge',
        'db.m2.xlarge',
        'db.m2.2xlarge',
        'db.m2.4xlarge',
    ],
    ConstraintDescription="must select a valid database instance type.",
))


db_engine_version = template.add_parameter(Parameter(
    "DatabaseEngineVersion",
    Default="",
    Description="Database engine version to use",
    Type="String",
))


db_multi_az = template.add_parameter(Parameter(
    "DatabaseMultiAZ",
    Default="false",
    Description="Whether or not to create a MultiAZ database",
    Type="String",
    AllowedValues=[
        "true",
        "false",
    ],
    ConstraintDescription="must choose true or false.",
))


db_allocated_storage = template.add_parameter(Parameter(
    "DatabaseAllocatedStorage",
    Default="20",
    Description="The size of the database (Gb)",
    Type="Number",
    MinValue="5",
    MaxValue="1024",
    ConstraintDescription="must be between 5 and 1024Gb.",
))


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
    DBName=Ref(db_name),
    AllocatedStorage=Ref(db_allocated_storage),
    DBInstanceClass=Ref(db_class),
    Engine="postgres",
    EngineVersion=Ref(db_engine_version),
    MultiAZ=Ref(db_multi_az),
    StorageType="gp2",
    MasterUsername=Ref(db_user),
    MasterUserPassword=Ref(db_password),
    DBSubnetGroupName=Ref(db_subnet_group),
    VPCSecurityGroups=[Ref(db_security_group)],
    BackupRetentionPeriod="7",
    DeletionPolicy="Snapshot",
)
