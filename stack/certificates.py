# Note: GovCloud doesn't support the certificate manager, so this file is
# only imported from load_balancer.py when we're not using GovCloud.

from troposphere import Equals, If, Not, Or, Ref
from troposphere.certificatemanager import Certificate, DomainValidationOption

from .common import dont_create_value
from .domain import domain_name, domain_name_alternates, no_alt_domains
from .template import template
from .utils import ParameterWithDefaults as Parameter

certificate_validation_method = template.add_parameter(
    Parameter(
        title="CertificateValidationMethod",
        Default=dont_create_value,
        AllowedValues=[dont_create_value, 'DNS', 'Email'],
        Type='String',
        Description=""
        "How to validate domain ownership for issuing an SSL certificate - "
        "highly recommend DNS. DNS and Email will pause stack creation until "
        "you do something to complete the validation. If omitted, an HTTPS "
        "listener can be manually attached to the load balancer after stack "
        "creation."
    ),
    group="Global",
    label="Certificate Validation Method"
)

custom_app_certificate_arn = template.add_parameter(
    Parameter(
        "CustomAppCertificateArn",
        Type="String",
        Description=""
        "An existing ACM certificate ARN to be used by the application ELB. "
        "DNS and Email validation will not work with this option.",
    ),
    group="Global",
    label="Custom App Certificate ARN",
)
custom_app_certificate_arn_condition = "CustomAppCertArnCondition"
template.add_condition(custom_app_certificate_arn_condition, Not(Equals(Ref(custom_app_certificate_arn), "")))

stack_cert_condition = "StackCertificateCondition"
template.add_condition(stack_cert_condition, Not(Equals(Ref(certificate_validation_method), dont_create_value)))

cert_condition = "CertificateCondition"
template.add_condition(cert_condition, Or(
    Not(Equals(Ref(custom_app_certificate_arn), "")),
    Not(Equals(Ref(certificate_validation_method), dont_create_value))
))

application = If(custom_app_certificate_arn_condition,
                 Ref(custom_app_certificate_arn),
                 Ref(template.add_resource(
                     Certificate(
                         'Certificate',
                         Condition=stack_cert_condition,
                         DomainName=domain_name,
                         SubjectAlternativeNames=If(no_alt_domains, Ref("AWS::NoValue"), domain_name_alternates),
                         DomainValidationOptions=[
                             DomainValidationOption(
                                 DomainName=domain_name,
                                 ValidationDomain=domain_name,
                             ),
                         ],
                         ValidationMethod=Ref(certificate_validation_method)
                     )
                 )))
