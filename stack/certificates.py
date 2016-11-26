from troposphere import Ref
from troposphere.certificatemanager import (
    Certificate,
    DomainValidationOption,
)

from .template import template
from .domain import domain_name


application = Ref(template.add_resource(
    Certificate(
        'Certificate',
        DomainName=domain_name,
        DomainValidationOptions=[
            DomainValidationOption(
                DomainName=domain_name,
                ValidationDomain=domain_name,
            ),
        ],
    )
))
