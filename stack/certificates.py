from troposphere import Ref
from troposphere.certificatemanager import Certificate, DomainValidationOption

from .domain import domain_name, domain_name_alternates
from .template import template

application = Ref(template.add_resource(
    Certificate(
        'Certificate',
        DomainName=domain_name,
        SubjectAlternativeNames=domain_name_alternates,
        DomainValidationOptions=[
            DomainValidationOption(
                DomainName=domain_name,
                ValidationDomain=domain_name,
            ),
        ],
    )
))
