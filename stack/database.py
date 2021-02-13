from collections import OrderedDict

from troposphere import (
    And,
    Condition,
    Equals,
    FindInMap,
    GetAtt,
    If,
    Join,
    Not,
    Output,
    Ref,
    Tags,
    ec2,
    rds
)

from .common import (
    cmk_arn,
    dont_create_value,
    use_aes256_encryption,
    use_cmk_arn
)
from .template import template
from .utils import ParameterWithDefaults as Parameter
from .vpc import private_subnet_a, private_subnet_b, private_subnet_a_cidr, private_subnet_b_cidr, vpc

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

# https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.DBInstanceClass.html
db_class = template.add_parameter(
    Parameter(
        "DatabaseClass",
        Default="db.t3.micro",
        Description="Database instance class",
        Type="String",
        AllowedValues=[
            dont_create_value,
            'db.r3.large',
            'db.r3.xlarge',
            'db.r3.2xlarge',
            'db.r3.4xlarge',
            'db.r3.8xlarge',
            'db.r4.large',
            'db.r4.xlarge',
            'db.r4.2xlarge',
            'db.r4.4xlarge',
            'db.r4.8xlarge',
            'db.r4.16xlarge',
            'db.r5.large',
            'db.r5.xlarge',
            'db.r5.2xlarge',
            'db.r5.4xlarge',
            'db.r5.8xlarge',
            'db.r5.12xlarge',
            'db.r5.16xlarge',
            'db.r5.24xlarge',
            'db.t2.micro',
            'db.t2.small',
            'db.t2.medium',
            'db.t2.large',
            'db.t3.micro',
            'db.t3.small',
            'db.t3.medium',
            'db.t3.large',
            'db.t3.xlarge',
            'db.t3.2xlarge',
            'db.m1.small',
            'db.m1.medium',
            'db.m1.large',
            'db.m1.xlarge',
            'db.m2.xlarge',
            'db.m2.2xlarge',
            'db.m2.4xlarge',
            'db.m3.medium',
            'db.m3.large',
            'db.m3.xlarge',
            'db.m3.2xlarge',
            'db.m4.large',
            'db.m4.xlarge',
            'db.m4.2xlarge',
            'db.m4.4xlarge',
            'db.m4.10xlarge',
            'db.m4.16xlarge',
            'db.m5.large',
            'db.m5.xlarge',
            'db.m5.2xlarge',
            'db.m5.4xlarge',
            'db.m5.8xlarge',
            'db.m5.12xlarge',
            'db.m5.16xlarge',
            'db.m5.24xlarge',
        ],
        ConstraintDescription="must select a valid database instance type.",
    ),
    group="Database",
    label="Instance Type",
)

db_condition = "DatabaseCondition"
template.add_condition(db_condition, Not(Equals(Ref(db_class), dont_create_value)))

db_replication = template.add_parameter(
    Parameter(
        "DatabaseReplication",
        Type="String",
        AllowedValues=["true", "false"],
        Default="false",
        Description="Whether to create a database server replica - "
        "WARNING this will fail if DatabaseBackupRetentionDays is 0.",
    ),
    group="Database",
    label="Database replication"
)
db_replication_condition = "DatabaseReplicationCondition"
template.add_condition(
    db_replication_condition,
    And(
        Condition(db_condition),
        Equals(Ref(db_replication), "true")
    )
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
        Description="Database version to use",
        Type="String",
    ),
    group="Database",
    label="Engine Version",
)

db_parameter_group_family = template.add_parameter(
    Parameter(
        "DatabaseParameterGroupFamily",
        Type="String",
        AllowedValues=[
            "aurora-mysql5.7",
            "docdb3.6",
            "neptune1",
            "aurora-postgresql9.6",
            "aurora-postgresql10",
            "mariadb10.0",
            "mariadb10.1",
            "mariadb10.2",
            "mariadb10.3",
            "mysql5.5",
            "mysql5.6",
            "mysql5.7",
            "mysql8.0",
            "oracle-ee-11.2",
            "oracle-ee-12.1",
            "oracle-ee-12.2",
            "oracle-se-11.2",
            "oracle-se1-11.2",
            "oracle-se2-12.1",
            "oracle-se2-12.2",
            "aurora5.6",
            "postgres9.3",
            "postgres9.4",
            "postgres9.5",
            "postgres9.6",
            "postgres10",
            "postgres11",
            "postgres12",
            "sqlserver-ee-11.0",
            "sqlserver-ee-12.0",
            "sqlserver-ee-13.0",
            "sqlserver-ee-14.0",
            "sqlserver-ex-11.0",
            "sqlserver-ex-12.0",
            "sqlserver-ex-13.0",
            "sqlserver-ex-14.0",
            "sqlserver-se-11.0",
            "sqlserver-se-12.0",
            "sqlserver-se-13.0",
            "sqlserver-se-14.0",
            "sqlserver-web-11.0",
            "sqlserver-web-12.0",
            "sqlserver-web-13.0",
            "sqlserver-web-14.0",
        ],
        Description="Database parameter group family name; must match the engine and version of "
                    "the RDS instance.",
    ),
    group="Database",
    label="Parameter Group Family",
)

db_parameter_group = rds.DBParameterGroup(
    "DatabaseParameterGroup",
    template=template,
    Condition=db_condition,
    Description="Database parameter group.",
    Family=Ref(db_parameter_group_family),
    Parameters={},
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

db_logging = template.add_parameter(
    Parameter(
        "DatabaseCloudWatchLogTypes",
        Default="",
        # For RDS on Postgres, an appropriate setting for this might be "postgresql,upgrade".
        # This parameter corresponds to the "EnableCloudwatchLogsExports" option on the DBInstance.
        # This option is not particularly well documented by AWS, but it looks like if you
        # go to the "Modify" screen via the RDS console you can see the types supported by your
        # instance. Then, lowercase it and remove " log" from the type, i.e., "Postgresql log"
        # will be come "postgresql" for this parameter.
        Description="A comma-separated list of the RDS log types (if any) to publish to "
                    "CloudWatch Logs. Note that log types are database engine-specific.",
        Type="CommaDelimitedList",
    ),
    group="Database",
    label="Database Log Types",
)

db_logging_condition = "DatabaseLoggingCondition"
template.add_condition(db_logging_condition, Not(Equals(Join(",", Ref(db_logging)), "")))

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
            CidrIp=private_subnet_a_cidr,
        ),
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort=FindInMap("RdsEngineMap", Ref(db_engine), "Port"),
            ToPort=FindInMap("RdsEngineMap", Ref(db_engine), "Port"),
            CidrIp=private_subnet_b_cidr,
        ),
    ],
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "rds"]),
    ),
)

db_subnet_group = rds.DBSubnetGroup(
    "DatabaseSubnetGroup",
    template=template,
    Condition=db_condition,
    DBSubnetGroupDescription="Subnets available for the RDS DB Instance",
    SubnetIds=[Ref(private_subnet_a), Ref(private_subnet_b)],
)

db_instance = rds.DBInstance(
    "DatabaseInstance",
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
    DBParameterGroupName=Ref(db_parameter_group),
    BackupRetentionPeriod=Ref(db_backup_retention_days),
    EnableCloudwatchLogsExports=If(db_logging_condition, Ref(db_logging), Ref("AWS::NoValue")),
    DeletionPolicy="Snapshot",
    KmsKeyId=If(use_cmk_arn, Ref(cmk_arn), Ref("AWS::NoValue")),
)

db_replica = rds.DBInstance(
    "DatabaseReplica",
    template=template,
    Condition=db_replication_condition,
    SourceDBInstanceIdentifier=Ref(db_instance),
    DBInstanceClass=Ref(db_class),
    Engine=Ref(db_engine),
    VPCSecurityGroups=[Ref(db_security_group)],
)

db_url = If(
    db_condition,
    Join("", [
        Ref(db_engine),
        "://",
        Ref(db_user),
        ":_PASSWORD_@",
        GetAtt(db_instance, 'Endpoint.Address'),
        ":",
        GetAtt(db_instance, 'Endpoint.Port'),
        "/",
        Ref(db_name),
    ]),
    "",  # defaults to empty string if no DB was created
)

db_replica_url = If(
    db_replication_condition,
    Join("", [
        Ref(db_engine),
        "://",
        Ref(db_user),
        ":_PASSWORD_@",
        GetAtt(db_replica, 'Endpoint.Address'),
        ":",
        GetAtt(db_replica, 'Endpoint.Port'),
        "/",
        Ref(db_name),
    ]),
    "",  # defaults to empty string if no DB was created
)

template.add_output([
    Output(
        "DatabaseURL",
        Description="URL to connect (without the password) to the database.",
        Value=db_url,
        Condition=db_condition,
    ),
])

template.add_output([
    Output(
        "DatabaseReplicaURL",
        Description="URL to connect (without the password) to the database replica.",
        Value=db_replica_url,
        Condition=db_replication_condition,
    ),
])

template.add_output([
    Output(
        "DatabasePort",
        Description="The port number on which the database accepts connections.",
        Value=GetAtt(db_instance, 'Endpoint.Port'),
        Condition=db_condition,
    ),
])

template.add_output([
    Output(
        "DatabaseAddress",
        Description="The connection endpoint for the database.",
        Value=GetAtt(db_instance, 'Endpoint.Address'),
        Condition=db_condition,
    ),
])

template.add_output([
    Output(
        "DatabaseReplicaAddress",
        Description="The connection endpoint for the database replica.",
        Value=GetAtt(db_replica, "Endpoint.Address"),
        Condition=db_replication_condition
    ),
])
