import os

from troposphere import (
    AWS_REGION,
    And,
    Equals,
    GetAtt,
    If,
    Join,
    Not,
    NoValue,
    Output,
    Ref,
    Split,
    iam
)
from troposphere.certificatemanager import Certificate, DomainValidationOption
from troposphere.cloudfront import (
    DefaultCacheBehavior,
    Distribution,
    DistributionConfig,
    ForwardedValues,
    Origin,
    S3OriginConfig,
    ViewerCertificate
)
from troposphere.s3 import (
    Bucket,
    BucketEncryption,
    CorsConfiguration,
    CorsRules,
    Private,
    PublicAccessBlockConfiguration,
    ServerSideEncryptionByDefault,
    ServerSideEncryptionRule,
    VersioningConfiguration
)

from .common import (
    arn_prefix,
    cmk_arn,
    use_aes256_encryption_cond,
    use_cmk_arn
)
from .domain import domain_name, domain_name_alternates, no_alt_domains
from .sftp import use_sftp_condition, use_sftp_with_kms_condition
from .template import template
from .utils import ParameterWithDefaults as Parameter

assets_bucket_access_control = template.add_parameter(
    Parameter(
        "AssetsBucketAccessControl",
        Default="PublicRead",
        Description="Canned ACL for the public S3 bucket. Private is recommended; it "
                    "allows for objects to be make publicly readable, but prevents "
                    "listing of the bucket contents.",
        Type="String",
        AllowedValues=[
            "PublicRead",
            "Private",
        ],
        ConstraintDescription="Must be PublicRead or Private.",
    ),
    group="Static Media",
    label="Assets Bucket ACL",
)

common_bucket_conf = dict(
    VersioningConfiguration=VersioningConfiguration(
        Status="Enabled"
    ),
    DeletionPolicy="Retain",
    CorsConfiguration=CorsConfiguration(
        CorsRules=[CorsRules(
            AllowedOrigins=Split(";", Join("", [
                "https://", domain_name,
                If(
                    no_alt_domains,
                    # if we don't have any alternate domains, return an empty string
                    "",
                    # otherwise, return the ';https://' that will be needed by the first domain
                    ";https://",
                ),
                # then, add all the alternate domains, joined together with ';https://'
                Join(";https://", domain_name_alternates),
                # now that we have a string of origins separated by ';', Split() is used to make it into a list again
            ])),
            AllowedMethods=[
                "POST",
                "PUT",
                "HEAD",
                "GET",
            ],
            AllowedHeaders=[
                "*",
            ],
        )],
    ),
)

# Create an S3 bucket that holds statics and media. Default to private to prevent
# public list permissions, but still allow objects to be made publicly readable.
assets_bucket = template.add_resource(
    Bucket(
        "AssetsBucket",
        AccessControl=Ref(assets_bucket_access_control),
        BucketEncryption=If(
            use_aes256_encryption_cond,
            BucketEncryption(
                ServerSideEncryptionConfiguration=[
                    ServerSideEncryptionRule(
                        ServerSideEncryptionByDefault=ServerSideEncryptionByDefault(
                            SSEAlgorithm='AES256'
                        )
                    )
                ]
            ),
            NoValue
        ),
        **common_bucket_conf,
    )
)


# Output S3 asset bucket name
template.add_output(
    Output(
        "AssetsBucketDomainName",
        Description="Assets bucket domain name",
        Value=GetAtt(assets_bucket, "DomainName"),
    )
)


# Create an S3 bucket that holds user uploads or other non-public files
private_assets_bucket = template.add_resource(
    Bucket(
        "PrivateAssetsBucket",
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
                            SSEAlgorithm=If(use_cmk_arn, 'aws:kms', 'AES256'),
                            KMSMasterKeyID=If(use_cmk_arn, Ref(cmk_arn), Ref("AWS::NoValue")),
                        )
                    )
                ]
            ),
            NoValue
        ),
        **common_bucket_conf,
    )
)

# Output S3 private assets bucket name
template.add_output(
    Output(
        "PrivateAssetsBucketDomainName",
        Description="Private assets bucket domain name",
        Value=GetAtt(private_assets_bucket, "DomainName"),
    )
)

# Bucket for SFTP service
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

assets_management_policy_statements = [
    dict(
        Effect="Allow",
        Action=["s3:ListBucket"],
        Resource=Join("", [arn_prefix, ":s3:::", Ref(assets_bucket)]),
    ),
    dict(
        Effect="Allow",
        Action=["s3:*"],
        Resource=Join("", [arn_prefix, ":s3:::", Ref(assets_bucket), "/*"]),
    ),
    dict(
        Effect="Allow",
        Action=["s3:ListBucket"],
        Resource=Join("", [arn_prefix, ":s3:::", Ref(private_assets_bucket)]),
    ),
    dict(
        Effect="Allow",
        Action=["s3:*"],
        Resource=Join("", [arn_prefix, ":s3:::", Ref(private_assets_bucket), "/*"]),
    ),
]

assets_management_policy_statements_including_sftp_bucket = (
    assets_management_policy_statements
    + [
        dict(
            Effect="Allow",
            Action=["s3:ListBucket"],
            Resource=Join("", [arn_prefix, ":s3:::", Ref(sftp_assets_bucket)]),
        ),
        dict(
            Effect="Allow",
            Action=["s3:*"],
            Resource=Join("", [arn_prefix, ":s3:::", Ref(sftp_assets_bucket), "/*"]),
        ),
    ]
)

# central asset management policy for use in instance roles
assets_management_policy = iam.Policy(
    PolicyName="AssetsManagementPolicy",
    PolicyDocument=dict(
        Statement=If(
            use_sftp_condition,
            assets_management_policy_statements_including_sftp_bucket,
            assets_management_policy_statements,
        )
    ),
)


if os.environ.get('USE_GOVCLOUD') != 'on':
    assets_use_cloudfront = template.add_parameter(
        Parameter(
            "AssetsUseCloudFront",
            Description="Whether or not to create a CloudFront distribution tied to the S3 assets bucket.",
            Type="String",
            AllowedValues=["true", "false"],
            Default="true",
        ),
        group="Static Media",
        label="Enable CloudFront",
    )
    assets_use_cloudfront_condition = "AssetsUseCloudFrontCondition"
    template.add_condition(assets_use_cloudfront_condition, Equals(Ref(assets_use_cloudfront), "true"))

    assets_cloudfront_domain = template.add_parameter(
        Parameter(
            "AssetsCloudFrontDomain",
            Description="A custom domain name (CNAME) for your CloudFront distribution, e.g., "
                        "\"static.example.com\".",
            Type="String",
            Default="",
        ),
        group="Static Media",
        label="CloudFront Custom Domain",
    )
    assets_custom_domain_condition = "AssetsCloudFrontDomainCondition"
    template.add_condition(assets_custom_domain_condition, Not(Equals(Ref(assets_cloudfront_domain), "")))

    assets_certificate_arn = template.add_parameter(
        Parameter(
            "AssetsCloudFrontCertArn",
            Description="If (1) you specified a custom static media domain, (2) your stack is NOT in the us-east-1 "
                        "region, and (3) you wish to serve static media over HTTPS, you must manually create an "
                        "ACM certificate in the us-east-1 region and provide its ARN here.",
            Type="String",
        ),
        group="Static Media",
        label="CloudFront SSL Certificate ARN",
    )
    assets_certificate_arn_condition = "AssetsCloudFrontCertArnCondition"
    template.add_condition(assets_certificate_arn_condition, Not(Equals(Ref(assets_certificate_arn), "")))

    # Currently, you can specify only certificates that are in the US East (N. Virginia) region.
    # http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-cloudfront-distributionconfig-viewercertificate.html
    assets_create_certificate_condition = "AssetsCreateCertificateCondition"
    template.add_condition(
        assets_create_certificate_condition,
        And(
            Not(Equals(Ref(assets_cloudfront_domain), "")),
            Equals(Ref(AWS_REGION), "us-east-1"),
            Equals(Ref(assets_certificate_arn), "")
        )
    )

    assets_certificate = template.add_resource(
        Certificate(
            'AssetsCertificate',
            Condition=assets_create_certificate_condition,
            DomainName=Ref(assets_cloudfront_domain),
            DomainValidationOptions=[
                DomainValidationOption(
                    DomainName=Ref(assets_cloudfront_domain),
                    ValidationDomain=Ref(assets_cloudfront_domain),
                ),
            ],
        )
    )

    # Create a CloudFront CDN distribution
    distribution = template.add_resource(
        Distribution(
            'AssetsDistribution',
            Condition=assets_use_cloudfront_condition,
            DistributionConfig=DistributionConfig(
                Aliases=If(assets_custom_domain_condition, [Ref(assets_cloudfront_domain)], Ref("AWS::NoValue")),
                # use the ACM certificate we created (if any), otherwise fall back to the manually-supplied
                # ARN (if any)
                ViewerCertificate=If(
                    assets_create_certificate_condition,
                    ViewerCertificate(
                        AcmCertificateArn=Ref(assets_certificate),
                        SslSupportMethod='sni-only',
                    ),
                    If(
                        assets_certificate_arn_condition,
                        ViewerCertificate(
                            AcmCertificateArn=Ref(assets_certificate_arn),
                            SslSupportMethod='sni-only',
                        ),
                        Ref("AWS::NoValue"),
                    ),
                ),
                Origins=[Origin(
                    Id="Assets",
                    DomainName=GetAtt(assets_bucket, "DomainName"),
                    S3OriginConfig=S3OriginConfig(
                        OriginAccessIdentity="",
                    ),
                )],
                DefaultCacheBehavior=DefaultCacheBehavior(
                    TargetOriginId="Assets",
                    ForwardedValues=ForwardedValues(
                        # Cache results *should* vary based on querystring (e.g., 'style.css?v=3')
                        QueryString=True,
                        # make sure headers needed by CORS policy above get through to S3
                        # http://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/header-caching.html#header-caching-web-cors
                        Headers=[
                            'Origin',
                            'Access-Control-Request-Headers',
                            'Access-Control-Request-Method',
                        ],
                    ),
                    ViewerProtocolPolicy="allow-all",
                ),
                Enabled=True
            ),
        )
    )

    # Output CloudFront url
    template.add_output(
        Output(
            "AssetsDistributionDomainName",
            Description="The assets CDN domain name",
            Value=GetAtt(distribution, "DomainName"),
            Condition=assets_use_cloudfront_condition,
        )
    )
else:
    distribution = None

# The scopedown policy is used to restrict a user's access to the parts of the bucket
# we don't want them to access.
common_sftp_scopedown_policy_statements = [
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

sftp_kms_policy_statement = dict(
    Effect="Allow",
    Action=["kms:DescribeKey", "kms:GenerateDataKey", "kms:Encrypt", "kms:Decrypt"],
    Resource=Ref(cmk_arn),
)

sftp_scopedown_policy = iam.ManagedPolicy(
    # This is for applying when adding users to the transfer server. It's not used directly in the stack creation,
    # other than adding it to IAM for later use.
    "SFTPUserScopeDownPolicy",
    PolicyDocument=dict(
        Version="2012-10-17",
        Statement=If(
            use_sftp_with_kms_condition,
            common_sftp_scopedown_policy_statements + [sftp_kms_policy_statement],
            common_sftp_scopedown_policy_statements,
        ),
    ),
)
template.add_resource(sftp_scopedown_policy)

# The ROLE is applied to users to let them access the bucket in general,
# without regart to who they are.
common_sftp_user_role_statements = [
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
                    common_sftp_user_role_statements + [sftp_kms_policy_statement],
                    common_sftp_user_role_statements,
                ),
            ),
        )
    ],
    RoleName=Join("-", [Ref("AWS::StackName"), "SFTPUserRole"]),
)
