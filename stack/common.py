from troposphere import Parameter, Ref

from .template import template

dont_create_value = "(none)"

arn_prefix = Ref(template.add_parameter(Parameter(
    "ArnPrefix",
    Description="The prefix to use for Amazon Resource Names (ARNs).",
    Type="String",
    Default="arn:aws",
    AllowedValues=["arn:aws", "arn:aws-us-gov"],
)))


container_instance_type = Ref(template.add_parameter(Parameter(
    "ContainerInstanceType",
    Description="The container instance type",
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
)))

secret_key = Ref(template.add_parameter(Parameter(
    "SecretKey",
    Description="Application secret key",
    Type="String",
)))
