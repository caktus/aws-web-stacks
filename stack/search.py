from awacs.aws import Action, Allow, Policy, Principal, Statement
from troposphere import Equals, GetAtt, Not, Output, Ref
from troposphere.elasticsearch import (
    Domain,
    EBSOptions,
    ElasticsearchClusterConfig
)

from .common import dont_create_value, instance_role
from .template import template
from .utils import ParameterWithDefaults as Parameter

es_instance_type = template.add_parameter(
    Parameter(
        "ElasticsearchInstanceType",
        Default=dont_create_value,
        Description="Elasticsearch instance type. Note: not all types are supported in all regions; see: "
                    "http://docs.aws.amazon.com/elasticsearch-service/latest/developerguide/"
                    "aes-supported-instance-types.html",
        Type="String",
        AllowedValues=[
            dont_create_value,
            't2.micro.elasticsearch',
            't2.small.elasticsearch',
            't2.medium.elasticsearch',
            'm3.medium.elasticsearch',
            'm3.large.elasticsearch',
            'm3.xlarge.elasticsearch',
            'm3.2xlarge.elasticsearch',
            'm4.large.elasticsearch',
            'm4.xlarge.elasticsearch',
            'm4.2xlarge.elasticsearch',
            'm4.4xlarge.elasticsearch',
            'm4.10xlarge.elasticsearch',
            'c4.large.elasticsearch',
            'c4.xlarge.elasticsearch',
            'c4.2xlarge.elasticsearch',
            'c4.4xlarge.elasticsearch',
            'c4.8xlarge.elasticsearch',
            'r3.large.elasticsearch',
            'r3.xlarge.elasticsearch',
            'r3.2xlarge.elasticsearch',
            'r3.4xlarge.elasticsearch',
            'r3.8xlarge.elasticsearch',
            'r4.large.elasticsearch',
            'r4.xlarge.elasticsearch',
            'r4.2xlarge.elasticsearch',
            'r4.4xlarge.elasticsearch',
            'r4.8xlarge.elasticsearch',
            'r4.16xlarge.elasticsearch',
            'i2.xlarge.elasticsearch',
            'i2.2xlarge.elasticsearch',
        ],
        ConstraintDescription="must select a valid Elasticsearch instance type.",
    ),
    group="Elasticsearch",
    label="Instance Type",
)

es_version = template.add_parameter(
    Parameter(
        "ElasticsearchVersion",
        Default="2.3",
        AllowedValues=[
            "1.5",
            "2.3",
            "5.1",
            "5.3",
        ],
        Description="Elasticsearch version. Note: t2.micro.elasticsearch instances support only versions 2.3 and 1.5.",
        Type="String",
        ConstraintDescription="must select a valid Elasticsearch version.",
    ),
    group="Elasticsearch",
    label="Version",
)

es_volume_size = template.add_parameter(
    Parameter(
        "ElasticsearchVolumeSize",
        Default="10",
        MinValue="10",
        MaxValue="1536",
        Description="Elasticsearch EBS volume size, in GB. Note: maximum volume size varies by instance type; see: "
                    "http://docs.aws.amazon.com/elasticsearch-service/latest/developerguide/aes-limits.html"
                    "#ebsresource.",
        Type="Number",
    ),
    group="Elasticsearch",
    label="Storage (GB)",
)

es_condition = "Elasticsearch"
template.add_condition(es_condition, Not(Equals(Ref(es_instance_type), dont_create_value)))


# Create an Elasticsearch domain
es_domain = template.add_resource(
    Domain(
        "ElasticsearchDomain",
        AccessPolicies=Policy(
            Statement=[
                Statement(
                    Effect=Allow,
                    Action=[Action("es", "*")],
                    Principal=Principal("AWS", [GetAtt(instance_role, "Arn")]),
                ),
            ]
        ),
        Condition=es_condition,
        EBSOptions=EBSOptions(
            EBSEnabled=True,
            VolumeSize=Ref(es_volume_size),
        ),
        ElasticsearchClusterConfig=ElasticsearchClusterConfig(
            InstanceType=Ref(es_instance_type),
        ),
        ElasticsearchVersion=Ref(es_version),
    )
)


# Output Elasticsearch domain endpoint and ARN
template.add_output(Output(
    "ElasticsearchDomainEndpoint",
    Description="Elasticsearch domain endpoint",
    Value=GetAtt(es_domain, "DomainEndpoint"),
    Condition=es_condition,
))

template.add_output(Output(
    "ElasticsearchDomainArn",
    Description="Elasticsearch domain ARN",
    Value=GetAtt(es_domain, "DomainArn"),
    Condition=es_condition,
))
