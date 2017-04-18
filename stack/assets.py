import os

from troposphere import (
    iam,
    Join,
    Output,
    GetAtt,
    Ref,
)

from troposphere.s3 import (
    AuthenticatedRead,
    Bucket,
    CorsConfiguration,
    CorsRules,
    PublicRead,
    VersioningConfiguration,
)

from troposphere.cloudfront import (
    DefaultCacheBehavior,
    Distribution,
    DistributionConfig,
    ForwardedValues,
    Origin,
    S3Origin,
)

from .common import arn_prefix
from .template import template
from .domain import domain_name


# Create an S3 bucket that holds statics and media
assets_bucket = template.add_resource(
    Bucket(
        "AssetsBucket",
        AccessControl=PublicRead,
        VersioningConfiguration=VersioningConfiguration(
            Status="Enabled"
        ),
        DeletionPolicy="Retain",
        CorsConfiguration=CorsConfiguration(
            CorsRules=[CorsRules(
                AllowedOrigins=[
                    Join("", ["https://", domain_name]),
                    Join("", ["https://*.", domain_name]),
                ],
                AllowedMethods=[
                    "POST",
                    "PUT",
                    "HEAD",
                    "GET",
                ],
                AllowedHeaders=[
                    "*",
                ]
            )]
        ),
    )
)


# Output S3 asset bucket name
template.add_output(Output(
    "AssetsBucketDomainName",
    Description="Assets bucket domain name",
    Value=GetAtt(assets_bucket, "DomainName")
))


# Create an S3 bucket that holds user uploads or other non-public files
private_assets_bucket = template.add_resource(
    Bucket(
        "PrivateAssetsBucket",
        AccessControl=AuthenticatedRead,
        VersioningConfiguration=VersioningConfiguration(
            Status="Enabled"
        ),
        DeletionPolicy="Retain",
        CorsConfiguration=CorsConfiguration(
            CorsRules=[CorsRules(
                AllowedOrigins=[
                    Join("", ["https://", domain_name]),
                    Join("", ["https://*.", domain_name]),
                ],
                AllowedMethods=[
                    "POST",
                    "PUT",
                    "HEAD",
                    "GET",
                ],
                AllowedHeaders=[
                    "*",
                ]
            )]
        ),
    )
)


# Output S3 asset bucket name
template.add_output(Output(
    "PrivateAssetsBucketDomainName",
    Description="Private assets bucket domain name",
    Value=GetAtt(private_assets_bucket, "DomainName")
))


# central asset management policy for use in instance roles
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
        ],
    ),
)


if os.environ.get('USE_GOVCLOUD') != 'on':
    # Create a CloudFront CDN distribution
    distribution = template.add_resource(
        Distribution(
            'AssetsDistribution',
            DistributionConfig=DistributionConfig(
                Origins=[Origin(
                    Id="Assets",
                    DomainName=GetAtt(assets_bucket, "DomainName"),
                    S3OriginConfig=S3Origin(
                        OriginAccessIdentity="",
                    ),
                )],
                DefaultCacheBehavior=DefaultCacheBehavior(
                    TargetOriginId="Assets",
                    ForwardedValues=ForwardedValues(
                        QueryString=False
                    ),
                    ViewerProtocolPolicy="allow-all",
                ),
                Enabled=True
            ),
        )
    )

    # Output CloudFront url
    template.add_output(Output(
        "AssetsDistributionDomainName",
        Description="The assest CDN domain name",
        Value=GetAtt(distribution, "DomainName")
    ))
else:
    distribution = None
