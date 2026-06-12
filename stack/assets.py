# S3 buckets for static assets and a CloudFront distribution to serve them.
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
    BucketPolicy,
    CorsConfiguration,
    CorsRules,
    OwnershipControls,
    OwnershipControlsRule,
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
from .domain import all_domains_list
from .template import template
from .utils import ParameterWithDefaults as Parameter

common_bucket_conf = dict(
    VersioningConfiguration=VersioningConfiguration(
        Status="Enabled"
    ),
    DeletionPolicy="Retain",
    UpdateReplacePolicy="Retain",
    CorsConfiguration=CorsConfiguration(
        CorsRules=[CorsRules(
            AllowedOrigins=Split(';', Join('', [
                'https://',
                Join(';https://', all_domains_list)
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

# Create an S3 bucket that holds static assets. All assets in this bucket
# are publicly readable; the private assets bucket should be used for non-public files.
assets_bucket = template.add_resource(
    Bucket(
        "AssetsBucket",
        OwnershipControls=OwnershipControls(
            Rules=[OwnershipControlsRule(ObjectOwnership="BucketOwnerEnforced")]
        ),
        PublicAccessBlockConfiguration=PublicAccessBlockConfiguration(
            BlockPublicAcls=False,
            BlockPublicPolicy=False,
            IgnorePublicAcls=False,
            RestrictPublicBuckets=False,
        ),
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

# Bucket policy to allow public read access to assets
template.add_resource(
    BucketPolicy(
        "AssetsBucketPolicy",
        Bucket=Ref(assets_bucket),
        PolicyDocument=dict(
            Version="2012-10-17",
            Statement=[
                dict(
                    Effect="Allow",
                    Principal="*",
                    Action="s3:GetObject",
                    Resource=Join("", [arn_prefix, ":s3:::", Ref(assets_bucket), "/*"]),
                ),
            ],
        ),
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

# Central asset management policy for use in instance roles
assets_management_policy = iam.Policy(
    PolicyName="AssetsManagementPolicy",
    PolicyDocument=dict(
        Statement=[
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
    ),
)

assets_use_cloudfront = template.add_parameter(
    Parameter(
        "AssetsUseCloudFront",
        Description="Create a CloudFront distribution for the assets bucket.",
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
        Description="Custom CloudFront domain name (optional).",
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
        Description="ACM certificate ARN for CloudFront HTTPS (outside us-east-1).",
        Type="String",
        Default="",
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
        Description="Assets CDN domain name",
        Value=GetAtt(distribution, "DomainName"),
        Condition=assets_use_cloudfront_condition,
    )
)
