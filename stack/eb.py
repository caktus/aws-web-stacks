from awacs import ecr
from awacs.aws import Allow, Policy, Principal, Statement
from awacs.sts import AssumeRole
from troposphere import FindInMap, GetAtt, Join, Output, Parameter, Ref, iam
from troposphere.elasticbeanstalk import (
    Application,
    Environment,
    OptionSettings
)
from troposphere.iam import InstanceProfile, Role

from .assets import assets_management_policy
from .certificates import application as application_certificate
from .common import container_instance_type
from .environment import environment_variables
from .logs import logging_policy
from .security_groups import (
    container_security_group,
    load_balancer_security_group
)
from .template import template
from .vpc import (
    USE_NAT_GATEWAY,
    container_a_subnet,
    container_b_subnet,
    loadbalancer_a_subnet,
    loadbalancer_b_subnet,
    vpc
)

solution_stack = template.add_parameter(
    Parameter(
        "SolutionStack",
        Description="Elastic Beanstalk solution stack name (do NOT change after "
                    "stack creation). You most likely want to copy the italicized "
                    "text from: http://docs.aws.amazon.com/elasticbeanstalk/latest"
                    "/dg/concepts.platforms.html#concepts.platforms.mcdocker",
        Type="String",
        Default="",
    ),
    group="Application Server",
    label="Solution Stack",
)

key_name = template.add_parameter(
    Parameter(
        "KeyName",
        Description="Name of an existing EC2 KeyPair to enable SSH access to "
                    "the AWS Elastic Beanstalk instance",
        Type="AWS::EC2::KeyPair::KeyName",
        ConstraintDescription="must be the name of an existing EC2 KeyPair."
    ),
    group="Application Server",
    label="SSH Key Name",
)

template.add_mapping("Region2Principal", {
    'ap-northeast-1': {
        'EC2Principal': 'ec2.amazonaws.com',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com'},
    'ap-southeast-1': {
        'EC2Principal': 'ec2.amazonaws.com',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com'},
    'ap-southeast-2': {
        'EC2Principal': 'ec2.amazonaws.com',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com'},
    'cn-north-1': {
        'EC2Principal': 'ec2.amazonaws.com.cn',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com.cn'},
    'eu-central-1': {
        'EC2Principal': 'ec2.amazonaws.com',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com'},
    'eu-west-1': {
        'EC2Principal': 'ec2.amazonaws.com',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com'},
    'sa-east-1': {
        'EC2Principal': 'ec2.amazonaws.com',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com'},
    'us-east-1': {
        'EC2Principal': 'ec2.amazonaws.com',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com'},
    'us-west-1': {
        'EC2Principal': 'ec2.amazonaws.com',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com'},
    'us-west-2': {
        'EC2Principal': 'ec2.amazonaws.com',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com'}
    }
)

web_server_role = Role(
    "WebServerRole",
    template=template,
    AssumeRolePolicyDocument=Policy(
        Statement=[
            Statement(
                Effect=Allow, Action=[AssumeRole],
                Principal=Principal(
                    "Service", [
                        FindInMap(
                            "Region2Principal",
                            Ref("AWS::Region"), "EC2Principal")
                    ]
                )
            )
        ]
    ),
    Path="/",
    Policies=[
        assets_management_policy,
        logging_policy,
        iam.Policy(
            PolicyName="EBBucketAccess",
            PolicyDocument=dict(
                Statement=[dict(
                    Effect="Allow",
                    Action=[
                        "s3:Get*",
                        "s3:List*",
                        "s3:PutObject",
                    ],
                    Resource=[
                        "arn:aws:s3:::elasticbeanstalk-*",
                        "arn:aws:s3:::elasticbeanstalk-*/*",
                    ],
                )],
            ),
        ),
        iam.Policy(
            PolicyName="EBXRayAccess",
            PolicyDocument=dict(
                Statement=[dict(
                    Effect="Allow",
                    Action=[
                        "xray:PutTraceSegments",
                        "xray:PutTelemetryRecords",
                    ],
                    Resource="*",
                )],
            ),
        ),
        iam.Policy(
            PolicyName="EBCloudWatchLogsAccess",
            PolicyDocument=dict(
                Statement=[dict(
                    Effect="Allow",
                    Action=[
                        "logs:PutLogEvents",
                        "logs:CreateLogStream",
                    ],
                    Resource="arn:aws:logs:*:*:log-group:/aws/elasticbeanstalk*",
                )],
            ),
        ),
        iam.Policy(
            PolicyName="ECSManagementPolicy",
            PolicyDocument=dict(
                Statement=[dict(
                    Effect="Allow",
                    Action=[
                        "ecs:*",
                        "elasticloadbalancing:*",
                    ],
                    Resource="*",
                )],
            ),
        ),
        iam.Policy(
            PolicyName='ECRManagementPolicy',
            PolicyDocument=dict(
                Statement=[dict(
                    Effect='Allow',
                    Action=[
                        ecr.GetAuthorizationToken,
                        ecr.GetDownloadUrlForLayer,
                        ecr.BatchGetImage,
                        ecr.BatchCheckLayerAvailability,
                    ],
                    Resource="*",
                )],
            ),
        ),
    ]
)

web_server_instance_profile = InstanceProfile(
    "WebServerInstanceProfile",
    template=template,
    Path="/",
    Roles=[Ref(web_server_role)],
)

eb_application = Application(
    "EBApplication",
    template=template,
    Description="AWS Elastic Beanstalk Application"
)

# eb_application_version = ApplicationVersion(
#     "EBApplicationVersion",
#     template=template,
#     Description="Version 1.0",
#     ApplicationName=Ref(eb_application),
#     SourceBundle=SourceBundle(
#         S3Bucket=Join("-", ["elasticbeanstalk-samples", Ref("AWS::Region")]),
#         S3Key="nodejs-sample.zip"
#     )
# )

template.add_resource(Environment(
    "EBEnvironment",
    Description="AWS Elastic Beanstalk Environment",
    ApplicationName=Ref(eb_application),
    SolutionStackName=Ref(solution_stack),

    OptionSettings=[
        # VPC settings
        OptionSettings(
            Namespace="aws:ec2:vpc",
            OptionName="VPCId",
            Value=Ref(vpc),
        ),
        OptionSettings(
            Namespace="aws:ec2:vpc",
            OptionName="AssociatePublicIpAddress",
            # instances need a public IP if we're not using a NAT gateway
            Value=str(not USE_NAT_GATEWAY).lower(),
        ),
        OptionSettings(
            Namespace="aws:ec2:vpc",
            OptionName="Subnets",
            Value=Join(",", [
                Ref(container_a_subnet),
                Ref(container_b_subnet),
            ]),
        ),
        OptionSettings(
            Namespace="aws:ec2:vpc",
            OptionName="ELBSubnets",
            Value=Join(",", [
                Ref(loadbalancer_a_subnet),
                Ref(loadbalancer_b_subnet),
            ]),
        ),
        # Launch config settings
        OptionSettings(
            Namespace="aws:autoscaling:launchconfiguration",
            OptionName="InstanceType",
            Value=container_instance_type,
        ),
        OptionSettings(
            Namespace="aws:autoscaling:launchconfiguration",
            OptionName="EC2KeyName",
            Value=Ref(key_name),
        ),
        OptionSettings(
            Namespace="aws:autoscaling:launchconfiguration",
            OptionName="IamInstanceProfile",
            Value=Ref(web_server_instance_profile),
        ),
        OptionSettings(
            Namespace="aws:autoscaling:launchconfiguration",
            OptionName="SecurityGroups",
            Value=Join(",", [
                Ref(container_security_group),
            ]),
        ),
        # Load balancer settings
        OptionSettings(
            Namespace="aws:elb:loadbalancer",
            OptionName="SecurityGroups",
            Value=Join(",", [
                Ref(load_balancer_security_group),
            ]),
        ),
        # HTTPS Listener (note, these will not appear in the console -- only
        # the deprecated options which we are not using will appear there).
        OptionSettings(
            Namespace="aws:elb:listener:443",
            OptionName="ListenerProtocol",
            Value="HTTPS",
        ),
        OptionSettings(
            Namespace="aws:elb:listener:443",
            OptionName="SSLCertificateId",
            Value=application_certificate,
        ),
        OptionSettings(
            Namespace="aws:elb:listener:443",
            OptionName="InstanceProtocol",
            Value="HTTP",
        ),
        OptionSettings(
            Namespace="aws:elb:listener:443",
            OptionName="InstancePort",
            Value="80",
        ),
        # OS management options
        # OptionSettings(
        #     Namespace="aws:elasticbeanstalk:environment",
        # # allows AWS to reboot our instances with security updates
        #     OptionName="ServiceRole",
        # # should be created by EB by default
        #     Value="${aws_iam_role.eb_service_role.name),",
        # ),
        # OptionSettings(
        #     Namespace="aws:elasticbeanstalk:healthreporting:system",
        #     OptionName="SystemType", # required for managed updates
        #     Value="enhanced",
        # ),
        # OptionSettings(
        #     Namespace="aws:elasticbeanstalk:managedactions",
        # # required for managed updates
        #     OptionName="ManagedActionsEnabled",
        #     Value="true",
        # ),
        # OptionSettings(
        #     Namespace="aws:elasticbeanstalk:managedactions",
        #     OptionName="PreferredStartTime",
        #     Value="Sun:02:00",
        # ),
        # OptionSettings(
        #     Namespace="aws:elasticbeanstalk:managedactions:platformupdate",
        #     OptionName="UpdateLevel",
        #     Value="minor", # or "patch", ("minor", provides more updates)
        # ),
        # OptionSettings(
        #     Namespace="aws:elasticbeanstalk:managedactions:platformupdate",
        #     OptionName="InstanceRefreshEnabled",
        #     Value="true", # refresh instances weekly
        # ),
        # Logging configuration
        OptionSettings(
            Namespace="aws:elasticbeanstalk:cloudwatch:logs",
            OptionName="StreamLogs",
            Value="true",
        ),
        OptionSettings(
            Namespace="aws:elasticbeanstalk:cloudwatch:logs",
            OptionName="DeleteOnTerminate",
            Value="false",
        ),
        OptionSettings(
            Namespace="aws:elasticbeanstalk:cloudwatch:logs",
            OptionName="RetentionInDays",
            Value="365",
        ),
        # Environment variables
        OptionSettings(
            Namespace="aws:elb:listener:443",
            OptionName="InstancePort",
            Value="80",
        ),
    ] + [
        OptionSettings(
            Namespace="aws:elasticbeanstalk:application:environment",
            OptionName=k,
            Value=v,
        ) for k, v in environment_variables
    ],
))

template.add_output(
    Output(
        "URL",
        Description="URL of the AWS Elastic Beanstalk Environment",
        Value=Join("", ["http://", GetAtt("EBEnvironment", "EndpointURL")])
    )
)
