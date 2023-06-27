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
    CustomOriginConfig,
    DefaultCacheBehavior,
    Distribution,
    DistributionConfig,
    ForwardedValues,
    Origin,
    ViewerCertificate
)

from .certificates import application as app_certificate
from .domain import all_domains_list
from .template import template

origin_domain_name = Ref(
    template.add_parameter(
        Parameter(
            "AppCloudFrontOriginDomainName",
            Description="Domain name of the origin server",
            Type="String",
            Default="",
        ),
        group="Application Server",
        label="CloudFront Origin Domain Name",
    )
)

instance_role = Ref(
    template.add_parameter(
        Parameter(
            "AppCloudFrontRoleArn",
            Description="ARN of the role to add IAM permissions for invalidating this distribution",
            Type="String",
            Default="",
        ),
        group="Application Server",
        label="CloudFront Role ARN",
    )
)

app_protocol_policy = template.add_parameter(
    Parameter(
        "AppCloudFrontProtocolPolicy",
        Description="The protocols allowed by the application server's CloudFront distribution. See: "
                    "http://docs.aws.amazon.com/cloudfront/latest/APIReference/API_DefaultCacheBehavior.html",
        Type="String",
        AllowedValues=["redirect-to-https", "https-only", "allow-all"],
        Default="redirect-to-https",
    ),
    group="Application Server",
    label="CloudFront Protocol Policy",
)

app_forwarded_headers = template.add_parameter(
    Parameter(
        "AppCloudFrontForwardedHeaders",
        Description=(
            "The headers that will be forwarded to the origin and used in the cache key. "
            "The 'Host' header is required for SSL on an Elastic Load Balancer, but it "
            "should NOT be passed to a Lambda Function URL."
        ),
        Type="CommaDelimitedList",
        Default="",
    ),
    group="Application Server",
    label="CloudFront Forwarded Headers",
)
app_forwarded_headers_condition = "AppCloudFrontForwardedHeadersCondition"
template.add_condition(app_forwarded_headers_condition, Not(Equals(Join("", Ref(app_forwarded_headers)), "")))

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
        'AppCloudFrontDistribution',
        DistributionConfig=DistributionConfig(
            Aliases=all_domains_list,
            HttpVersion="http2",
            # If we're in us-east-1, use the application certificate tied to the load balancer, otherwise,
            # use the manually-created cert
            ViewerCertificate=If(
                us_east_1_condition,
                ViewerCertificate(
                    AcmCertificateArn=app_certificate,
                    SslSupportMethod='sni-only',
                    # Default/recommended on the AWS console, as of May, 2023
                    MinimumProtocolVersion='TLSv1.2_2021',
                ),
                If(
                    app_certificate_arn_condition,
                    ViewerCertificate(
                        AcmCertificateArn=Ref(app_certificate_arn),
                        SslSupportMethod='sni-only',
                        MinimumProtocolVersion='TLSv1.2_2021',
                    ),
                    Ref("AWS::NoValue"),
                ),
            ),
            Origins=[Origin(
                Id="ApplicationServer",
                DomainName=origin_domain_name,
                CustomOriginConfig=CustomOriginConfig(
                    OriginProtocolPolicy="https-only",
                ),
            )],
            DefaultCacheBehavior=DefaultCacheBehavior(
                TargetOriginId="ApplicationServer",
                Compress="true",
                AllowedMethods=["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"],
                CachedMethods=["HEAD", "GET"],
                ForwardedValues=ForwardedValues(
                    # This is a custom origin, so make sure everything (querystring, headers, cookies) are
                    # passed through to the origin server
                    QueryString=True,
                    Cookies=Cookies(
                        Forward='all',
                    ),
                    Headers=If(
                        app_forwarded_headers_condition,
                        Ref(app_forwarded_headers),
                        Ref("AWS::NoValue"),
                    ),
                ),
                ViewerProtocolPolicy=Ref(app_protocol_policy),
            ),
            Enabled=True,
        ),
    )
)

invalidation_policy = template.add_resource(
    iam.PolicyType(
        "AppCloudFrontInvalidationPolicy",
        PolicyName="AppCloudFrontInvalidationPolicy",
        PolicyDocument=dict(
            Statement=[
                dict(
                    Effect="Allow",
                    Action=[
                        "cloudfront:GetDistribution",
                        "cloudfront:GetDistributionConfig",
                        "cloudfront:ListDistributions",
                        "cloudfront:ListCloudFrontOriginAccessIdentities",
                        "cloudfront:CreateInvalidation",
                        "cloudfront:GetInvalidation",
                        "cloudfront:ListInvalidations",
                    ],
                    Resource="*",
                    # TODO: if/when CloudFront supports resource-level IAM permissions, enable them, e.g.:
                    # Resource=Join("", [arn_prefix, ":cloudfront:::distribution/", Ref(app_distribution)]),
                    # See: https://stackoverflow.com/a/29563986/166053
                ),
            ],
        ),
        Roles=[instance_role],
    )
)

# Output CloudFront url
template.add_output(Output(
    "AppCloudFrontDomainName",
    Description="The app CDN domain name",
    Value=GetAtt(app_distribution, "DomainName"),
))
