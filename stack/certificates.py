# Note: GovCloud doesn't support the certificate manager, so this file is
# only imported from load_balancer.py when we're not using GovCloud.

from troposphere import If, Ref
from troposphere.certificatemanager import Certificate, DomainValidationOption

from .domain import domain_name, domain_name_alternates, no_alt_domains
from .template import template
from .utils import ParameterWithDefaults as Parameter

certificate_validation_method = template.add_parameter(
    Parameter(
        title="CertificateValidationMethod",
        Default="DNS",
        AllowedValues=['DNS', 'Email'],
        Type='String',
        Description=""
        "How to validate domain ownership for issuing an SSL certificate - "
        "highly recommend DNS. Either way, stack creation will pause until "
        "you do something to complete the validation."
    ),
    group="Global",
    label="Certificate Validation Method"
)

application = Ref(template.add_resource(
    Certificate(
        'Certificate',
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
))
