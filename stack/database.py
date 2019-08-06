from collections import OrderedDict

from troposphere import Equals, FindInMap, Not, Ref, ec2, rds

from .common import dont_create_value, use_aes256_encryption
from .template import template
from .utils import ParameterWithDefaults as Parameter
from .vpc import (
    container_a_subnet,
    container_a_subnet_cidr,
    container_b_subnet,
    container_b_subnet_cidr,
    vpc
)

rds_engine_map = OrderedDict([
    ("aurora", {"Port": "3306"}),
    ("mariadb", {"Port": "3306"}),
    ("mysql", {"Port": "3306"}),
    ("oracle-ee", {"Port": "1521"}),
    ("oracle-se2", {"Port": "1521"}),
    ("oracle-se1", {"Port": "1521"}),
    ("oracle-se", {"Port": "1521"}),
    ("postgres", {"Port": "5432"}),
    ("sqlserver-ee", {"Port": "1433"}),
    ("sqlserver-se", {"Port": "1433"}),
    ("sqlserver-ex", {"Port": "1433"}),
    ("sqlserver-web", {"Port": "1433"}),
])
template.add_mapping('RdsEngineMap', rds_engine_map)

db_class = template.add_parameter(
    Parameter(
        "DatabaseClass",
        Default="db.t2.micro",
        Description="Database instance class",
        Type="String",
        AllowedValues=[
            dont_create_value,
            'db.t1.micro',
            'db.m1.small',
            'db.m4.large',
            'db.m4.xlarge',
            'db.m4.2xlarge',
            'db.m4.4xlarge',
            'db.m4.10xlarge',
            'db.r4.large',
            'db.r4.xlarge',
            'db.r4.2xlarge',
            'db.r4.4xlarge',
            'db.r4.8xlarge',
            'db.r4.16xlarge',
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
    ),
    group="Database",
    label="Instance Type",
)

db_engine = template.add_parameter(
    Parameter(
        "DatabaseEngine",
        Default="postgres",
        Description="Database engine to use",
        Type="String",
        AllowedValues=list(rds_engine_map.keys()),
        ConstraintDescription="must select a valid database engine.",
    ),
    group="Database",
    label="Engine",
)

db_engine_version = template.add_parameter(
    Parameter(
        "DatabaseEngineVersion",
        Default="",
        Description="Postgres version to use",
        Type="String",
    ),
    group="Database",
    label="Engine Version",
)

db_name = template.add_parameter(
    Parameter(
        "DatabaseName",
        Default="app",
        Description="Name of the database to create in the database server",
        Type="String",
        MinLength="1",
        MaxLength="64",
        AllowedPattern="[a-zA-Z][a-zA-Z0-9_]*",
        ConstraintDescription=(
            "must begin with a letter and contain only"
            " alphanumeric characters."
        )
    ),
    group="Database",
    label="Database Name",
)

db_user = template.add_parameter(
    Parameter(
        "DatabaseUser",
        Default="app",
        Description="The database admin account username",
        Type="String",
        MinLength="1",
        MaxLength="63",
        AllowedPattern="[a-zA-Z][a-zA-Z0-9_]*",
        ConstraintDescription=(
            "must begin with a letter and contain only"
            " alphanumeric characters and underscores."
        )
    ),
    group="Database",
    label="Username",
)

db_password = template.add_parameter(
    Parameter(
        "DatabasePassword",
        NoEcho=True,
        Description=''
        '''The database admin account password must consist of 10-41 printable'''
        '''ASCII characters *except* "/", """, or "@".''',
        Type="String",
        MinLength="10",
        MaxLength="41",
        AllowedPattern="[ !#-.0-?A-~]*",  # see http://www.catonmat.net/blog/my-favorite-regex/
        ConstraintDescription="must consist of 10-41 printable ASCII "
                              "characters except \"/\", \"\"\", or \"@\"."
    ),
    group="Database",
    label="Password",
)

db_allocated_storage = template.add_parameter(
    Parameter(
        "DatabaseAllocatedStorage",
        Default="20",
        Description="The size of the database (Gb)",
        Type="Number",
        MinValue="5",
        MaxValue="1024",
        ConstraintDescription="must be between 5 and 1024Gb.",
    ),
    group="Database",
    label="Storage (GB)",
)

db_multi_az = template.add_parameter(
    Parameter(
        "DatabaseMultiAZ",
        Default="false",
        Description="Whether or not to create a MultiAZ database",
        Type="String",
        AllowedValues=[
            "true",
            "false",
        ],
        ConstraintDescription="must choose true or false.",
    ),
    group="Database",
    label="Enable MultiAZ"
)

db_backup_retention_days = template.add_parameter(
    Parameter(
        "DatabaseBackupRetentionDays",
        Default="30",
        Description="The number of days for which automated backups are retained. Setting to 0 "
                    "disables automated backups.",
        Type="Number",
        AllowedValues=[str(x) for x in range(36)],  # 0-35 are the supported values
    ),
    group="Database",
    label="Backup Retention Days",
)

db_condition = "DatabaseCondition"
template.add_condition(db_condition, Not(Equals(Ref(db_class), dont_create_value)))

db_security_group = ec2.SecurityGroup(
    'DatabaseSecurityGroup',
    template=template,
    GroupDescription="Database security group.",
    Condition=db_condition,
    VpcId=Ref(vpc),
    SecurityGroupIngress=[
        # Rds Port in from web clusters
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort=FindInMap("RdsEngineMap", Ref(db_engine), "Port"),
            ToPort=FindInMap("RdsEngineMap", Ref(db_engine), "Port"),
            CidrIp=container_a_subnet_cidr,
        ),
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort=FindInMap("RdsEngineMap", Ref(db_engine), "Port"),
            ToPort=FindInMap("RdsEngineMap", Ref(db_engine), "Port"),
            CidrIp=container_b_subnet_cidr,
        ),
    ],
)

db_subnet_group = rds.DBSubnetGroup(
    "DatabaseSubnetGroup",
    template=template,
    Condition=db_condition,
    DBSubnetGroupDescription="Subnets available for the RDS DB Instance",
    SubnetIds=[Ref(container_a_subnet), Ref(container_b_subnet)],
)

db_instance = rds.DBInstance(
    # TODO: rename this resource to something generic along with the next major release
    "PostgreSQL",
    template=template,
    DBName=Ref(db_name),
    Condition=db_condition,
    AllocatedStorage=Ref(db_allocated_storage),
    DBInstanceClass=Ref(db_class),
    Engine=Ref(db_engine),
    EngineVersion=Ref(db_engine_version),
    MultiAZ=Ref(db_multi_az),
    StorageEncrypted=use_aes256_encryption,
    StorageType="gp2",
    MasterUsername=Ref(db_user),
    MasterUserPassword=Ref(db_password),
    DBSubnetGroupName=Ref(db_subnet_group),
    VPCSecurityGroups=[Ref(db_security_group)],
    BackupRetentionPeriod=Ref(db_backup_retention_days),
    DeletionPolicy="Snapshot",
)
