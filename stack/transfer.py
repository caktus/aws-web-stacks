from troposphere import (
    Equals,
    iam,
    Join,
    Parameter,
    Ref,
    Tags,
    transfer,
)

from .assets import private_assets_bucket
from .common import (
    arn_prefix,
)
from .template import template

use_transfer_server = template.add_parameter(
    Parameter(
        "UseTransferServer",
        Description="Whether or not to create a AWS Transfer Server.",
        Type="String",
        AllowedValues=["true", "false"],
        Default="false",
    ),
    group="SFTP",
    label="Enable SFTP Server",
)
use_transfer_server_condition = "UseTransferServer"
template.add_condition(use_transfer_server_condition, Equals(Ref(use_transfer_server), "true"))


transfer_server = transfer.Server(
    "TransferServer",
    template=template,
    Condition=use_transfer_server_condition,
    IdentityProviderType="SERVICE_MANAGED",
    EndpointType="PUBLIC",
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "sftp"]),
    ),
)

sftp_rw_policy = iam.Policy(
    PolicyName="SFTPS3RWPolicy",
    PolicyDocument=dict(
        Statement=[
            dict(
                Effect="Allow",
                Action=[
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                ],
                Resource=Join("", [arn_prefix, ":s3:::", Ref(private_assets_bucket)]),
            ),
            dict(
                Effect="Allow",
                Action=[
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:DeleteObject",
                    "s3:DeleteObjectVersion",
                    "s3:GetObjectVersion",
                    "s3:GetObjectACL",
                    "s3:PutObjectACL",
                ],
                Resource=Join("", [arn_prefix, ":s3:::", Ref(private_assets_bucket), "/*"]),
            ),
        ],
    ),
)

transfer_role = iam.Role(
    "AWSTransferRole",
    template=template,
    Condition=use_transfer_server_condition,
    AssumeRolePolicyDocument=dict(Statement=[dict(
        Effect="Allow",
        Principal=dict(Service=["transfer.amazonaws.com"]),
        Action=["sts:AssumeRole"],
    )]),
    Policies=[
        sftp_rw_policy,
    ],
    RoleName=Join("-", [Ref("AWS::StackName"), "AWSTransferRole"]),
)
