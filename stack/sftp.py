from troposphere import (
    And,
    Condition,
    Equals,
    GetAtt,
    If,
    Join,
    Not,
    NoValue,
    Output,
    Parameter,
    Ref,
    Tags,
    iam,
    transfer,
)
from troposphere.s3 import (
    Bucket,
    BucketEncryption,
    Private,
    PublicAccessBlockConfiguration,
    ServerSideEncryptionByDefault,
    ServerSideEncryptionRule,
)

from .assets import common_bucket_conf
from .common import arn_prefix, cmk_arn, use_aes256_encryption_cond, use_cmk_arn
from .template import template

use_sftp_server = template.add_parameter(
    Parameter(
        "UseSFTPServer",
        Description="Whether or not to set up an SFTP service.  If 'true', this will set up a transfer server and "
        "add an S3 bucket for its use, along with a role and policies for use when adding users.",
        Type="String",
        AllowedValues=["true", "false"],
        Default="false",
    ),
    group="SFTP",
    label="Enable SFTP Server",
)

use_sftp_condition = "UseSFTPServerCondition"
use_sftp_with_kms_condition = "UseSFTPWithKMSCondition"
use_sftp_without_kms_condition = "UseSFTPWithoutKMSCondition"

template.add_condition(use_sftp_condition, Equals(Ref(use_sftp_server), "true"))
template.add_condition(
    # If this condition is true, we need to create policies and roles that give
    # access to the customer KMS.
    use_sftp_with_kms_condition,
    And(
        Equals(Ref(use_sftp_server), "true"),
        Condition(use_aes256_encryption_cond),
        Condition(use_cmk_arn),
    ),
)
template.add_condition(
    # If this condition is true, we need to create policies and roles,
    # but they should not give access to customer KMS.
    use_sftp_without_kms_condition,
    And(Equals(Ref(use_sftp_server), "true"), Not(Condition(use_cmk_arn))),
)

sftp_assets_bucket = Bucket(
    "SFTPAssetsBucket",
    Condition=use_sftp_condition,
    AccessControl=Private,
    PublicAccessBlockConfiguration=PublicAccessBlockConfiguration(
        BlockPublicAcls=True,
        BlockPublicPolicy=True,
        IgnorePublicAcls=True,
        RestrictPublicBuckets=True,
    ),
    BucketEncryption=If(
        use_aes256_encryption_cond,
        BucketEncryption(
            ServerSideEncryptionConfiguration=[
                ServerSideEncryptionRule(
                    ServerSideEncryptionByDefault=ServerSideEncryptionByDefault(
                        SSEAlgorithm=If(use_cmk_arn, "aws:kms", "AES256"),
                        KMSMasterKeyID=If(
                            use_cmk_arn, Ref(cmk_arn), Ref("AWS::NoValue")
                        ),
                    )
                )
            ]
        ),
        NoValue,
    ),
    **common_bucket_conf,
)
template.add_resource(sftp_assets_bucket)

# Output SFTP asset bucket name
template.add_output(
    Output(
        "SFTPBucketDomainName",
        Condition=use_sftp_condition,
        Description="SFTP bucket domain name",
        Value=GetAtt(sftp_assets_bucket, "DomainName"),
    )
)


transfer_server = transfer.Server(
    "TransferServer",
    template=template,
    Condition=use_sftp_condition,
    IdentityProviderType="SERVICE_MANAGED",
    EndpointType="PUBLIC",
    Tags=Tags(Name=Join("-", [Ref("AWS::StackName"), "sftp"])),
)

"""
# WORKING SCOPEDOWN POLICY:
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "kms:DescribeKey",
                "kms:GenerateDataKey",
                "kms:Encrypt",
                "kms:Decrypt"
            ],
            "Resource": "arn:aws:kms:us-east-1:XXXXXX"
        },
        {
            "Sid": "AllowListingOfUserFolder",
            "Action": [
                "s3:ListBucket"
            ],
            "Effect": "Allow",
            "Resource": [
                "arn:aws:s3:::${transfer:HomeBucket}"
            ],
            "Condition": {
                "StringLike": {
                    "s3:prefix": [
                        "${transfer:UserName}/*",
                        "${transfer:UserName}"
                    ]
                }
            }
        },
        {
            "Sid": "HomeDirObjectAccess",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObjectVersion",
                "s3:DeleteObject",
                "s3:GetObjectVersion"
            ],
            "Resource": [
                "arn:aws:s3:::sftp-staging.forcetherapeutics.com/${transfer:UserName}",
                "arn:aws:s3:::sftp-staging.forcetherapeutics.com/${transfer:UserName}/*"
            ]
        }
    ]
}
"""


# The scopedown policy is used to restrict a user's access to the parts of the bucket
# we don't want them to access.
common_scopedown_policy_statements = [
    {
        "Sid": "AllowListingOfSFTPUserFolder",
        "Action": ["s3:ListBucket"],
        "Effect": "Allow",
        "Resource": ["arn:aws:s3:::${transfer:HomeBucket}"],
        "Condition": {
            "StringLike": {
                "s3:prefix": ["${transfer:UserName}/*", "${transfer:UserName}"]
            }
        },
    },
    {
        "Sid": "HomeDirObjectAccess",
        "Effect": "Allow",
        "Action": [
            "s3:PutObject",
            "s3:GetObject",
            "s3:DeleteObjectVersion",
            "s3:DeleteObject",
            "s3:GetObjectVersion",
        ],
        "Resource": [
            Join("/", [GetAtt(sftp_assets_bucket, "Arn"), "${transfer:UserName}"]),
            Join("/", [GetAtt(sftp_assets_bucket, "Arn"), "${transfer:UserName}/*"]),
        ],
    },
]

kms_policy_statement = dict(
    Effect="Allow",
    Action=["kms:DescribeKey", "kms:GenerateDataKey", "kms:Encrypt", "kms:Decrypt"],
    Resource=Ref(cmk_arn),
)

scopedown_policy = iam.ManagedPolicy(
    # This is for applying when adding users to the transfer server. It's not used directly in the stack creation,
    # other than adding it to IAM for later use.
    "SFTPUserScopeDownPolicy",
    PolicyDocument=dict(
        Version="2012-10-17",
        Statement=If(
            use_sftp_with_kms_condition,
            common_scopedown_policy_statements + [kms_policy_statement],
            common_scopedown_policy_statements,
        ),
    ),
)
template.add_resource(scopedown_policy)

# The ROLE is applied to users to let them access the bucket in general,
# without regart to who they are.
common_role_statements = [
    dict(
        Effect="Allow",
        Action=["s3:ListBucket", "s3:GetBucketLocation"],
        Resource=Join("", [arn_prefix, ":s3:::", Ref(sftp_assets_bucket)]),
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
        Resource=Join("", [arn_prefix, ":s3:::", Ref(sftp_assets_bucket), "/*"]),
    ),
]

sftp_user_role = iam.Role(
    # This also is not used directly during the stack setup, but is put into IAM
    # to be used later when adding users to the transfer server.
    "SFTPUserRole",
    template=template,
    AssumeRolePolicyDocument=dict(
        Statement=[
            dict(
                Effect="Allow",
                Principal=dict(Service=["transfer.amazonaws.com"]),
                Action=["sts:AssumeRole"],
            )
        ]
    ),
    Policies=[
        iam.Policy(
            "SFTPSUserRolePolicy",
            PolicyName="SFTPSUserRolePolicy",
            PolicyDocument=dict(
                Version="2012-10-17",
                Statement=If(
                    use_sftp_with_kms_condition,
                    common_role_statements + [kms_policy_statement],
                    common_role_statements,
                ),
            ),
        )
    ],
    RoleName=Join("-", [Ref("AWS::StackName"), "SFTPUserRole"]),
)
