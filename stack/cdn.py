import os

from troposphere import (
    AWS_REGION,
    Equals,
    GetAtt,
    If,
    Join,
    Not,
    Output,
    Parameter,
    Ref,
    iam
)
from troposphere.cloudfront import (
    Cookies,
    CustomOrigin,
    DefaultCacheBehavior,
    Distribution,
    DistributionConfig,
    ForwardedValues,
    Origin,
    ViewerCertificate
)

from .certificates import application as app_certificate
from .common import arn_prefix, instance_role
from .domain import all_domains_list
from .template import template

if os.getenv('USE_EB') == 'on':
    origin_domain_name = GetAtt("EBEnvironment", "EndpointURL")
elif os.getenv('USE_DOKKU') != 'on':
    # only import load_balancer if it's needed (not supported by Dokku stack yet)
    from .load_balancer import load_balancer
    origin_domain_name = GetAtt(load_balancer, "DNSName")
else:
    origin_domain_name = None
    app_distribution = None
    app_uses_cloudfront_condition = None

if origin_domain_name:
    app_uses_cloudfront = template.add_parameter(
        Parameter(
            "AppUsesCloudFront",
            Description="Whether or not to create a CloudFront distribution in front of your application server.",
            Type="String",
            AllowedValues=["true", "false"],
            Default="false",
        ),
        group="Application Server",
        label="Enable CloudFront",
    )
    app_uses_cloudfront_condition = "AppUsesCloudFrontCondition"
    template.add_condition(app_uses_cloudfront_condition, Equals(Ref(app_uses_cloudfront), "true"))

    # Currently, you can specify only certificates that are in the US East (N. Virginia) region.
    # http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-cloudfront-distributionconfig-viewercertificate.html
    us_east_1_condition = "UsEast1Condition"
    template.add_condition(
        us_east_1_condition,
        Equals(Ref(AWS_REGION), "us-east-1"),
    )

    app_certificate_arn = template.add_parameter(
        Parameter(
            "AppCloudFrontCertArn",
            Description="If your stack is NOT in the us-east-1 you must manually create an ACM certificate for "
                        "your application domain in the us-east-1 region and provide its ARN here.",
            Type="String",
        ),
        group="Application Server",
        label="CloudFront SSL Certificate ARN",
    )
    app_certificate_arn_condition = "AppCloudFrontCertArnCondition"
    template.add_condition(app_certificate_arn_condition, Not(Equals(Ref(app_certificate_arn), "")))

    # Create a CloudFront CDN distribution
    app_distribution = template.add_resource(
        Distribution(
            'AppDistribution',
            Condition=app_uses_cloudfront_condition,
            DistributionConfig=DistributionConfig(
                Aliases=all_domains_list,
                # If we're in us-east-1, use the application certificate tied to the load balancer, otherwise,
                # use the manually-created cert
                ViewerCertificate=If(
                    us_east_1_condition,
                    ViewerCertificate(
                        AcmCertificateArn=app_certificate,
                        SslSupportMethod='sni-only',
                    ),
                    If(
                        app_certificate_arn_condition,
                        ViewerCertificate(
                            AcmCertificateArn=Ref(app_certificate_arn),
                            SslSupportMethod='sni-only',
                        ),
                        Ref("AWS::NoValue"),
                    ),
                ),
                Origins=[Origin(
                    Id="ApplicationServer",
                    DomainName=origin_domain_name,
                    CustomOriginConfig=CustomOrigin(
                        OriginProtocolPolicy="match-viewer",
                    ),
                )],
                DefaultCacheBehavior=DefaultCacheBehavior(
                    TargetOriginId="ApplicationServer",
                    ForwardedValues=ForwardedValues(
                        # This is a custom origin, so make sure everything (querystring, headers, cookies) are
                        # passed through to the origin server
                        QueryString=True,
                        Cookies=Cookies(
                            Forward='all',
                        ),
                        Headers=[
                            'Host',  # required for SSL on an Elastic Load Balancer
                        ],
                    ),
                    ViewerProtocolPolicy="allow-all",
                ),
                Enabled=True,
            ),
        )
    )

    invalidation_policy = template.add_resource(
        iam.PolicyType(
            "AppDistributionInvalidationPolicy",
            PolicyName="AppDistributionInvalidationPolicy",
            PolicyDocument=dict(
                Statement=[
                    dict(
                        Effect="Allow",
                        Action=["cloudfront:*"],
                        Resource=Join("", [arn_prefix, ":s3:::", Ref(app_distribution)]),
                    ),
                ],
            ),
            Roles=[Ref(instance_role)],
        )
    )

    # Output CloudFront url
    template.add_output(Output(
        "AppDistributionDomainName",
        Description="The app CDN domain name",
        Value=GetAtt(app_distribution, "DomainName"),
        Condition=app_uses_cloudfront_condition,
    ))
