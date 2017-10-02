from troposphere import AWS_REGION, Equals, If, Parameter, Ref

from .template import template

dont_create_value = "(none)"

in_govcloud_region = "InGovCloudRegion"
template.add_condition(in_govcloud_region, Equals(Ref(AWS_REGION), "us-gov-west-1"))
arn_prefix = If(in_govcloud_region, "arn:aws-us-gov", "arn:aws")

container_instance_type = Ref(template.add_parameter(
    Parameter(
        "ContainerInstanceType",
        Description="The application server instance type",
        Type="String",
        Default="t2.micro",
        AllowedValues=[
            't2.nano',
            't2.micro',
            't2.small',
            't2.medium',
            't2.large',
            't2.xlarge',
            't2.2xlarge',
            'm4.large',
            'm4.xlarge',
            'm4.2xlarge',
            'm4.4xlarge',
            'm4.10xlarge',
            'm4.16xlarge',
            'm3.medium',
            'm3.large',
            'm3.xlarge',
            'm3.2xlarge',
            'c4.large',
            'c4.xlarge',
            'c4.2xlarge',
            'c4.4xlarge',
            'c4.8xlarge',
            'c3.large',
            'c3.xlarge',
            'c3.2xlarge',
            'c3.4xlarge',
            'c3.8xlarge',
            'p2.xlarge',
            'p2.8xlarge',
            'p2.16xlarge',
            'g2.2xlarge',
            'g2.8xlarge',
            'x1.16large',
            'x1.32xlarge',
            'r4.large',
            'r4.xlarge',
            'r4.2xlarge',
            'r4.4xlarge',
            'r4.8xlarge',
            'r4.16xlarge',
            'r3.large',
            'r3.xlarge',
            'r3.2xlarge',
            'r3.4xlarge',
            'r3.8xlarge',
            'i3.large',
            'i3.xlarge',
            'i3.2xlarge',
            'i3.4xlarge',
            'i3.8xlarge',
            'i3.16large',
            'd2.xlarge',
            'd2.2xlarge',
            'd2.4xlarge',
            'd2.8xlarge',
            'f1.2xlarge',
            'f1.16xlarge',
        ]
    ),
    group="Application Server",
    label="Instance Type",
))

secret_key = Ref(template.add_parameter(
    Parameter(
        "SecretKey",
        Description="Application secret key for this stack (optional)",
        Type="String",
        NoEcho=True,
    ),
    group="Application Server",
    label="Secret Key",
))
