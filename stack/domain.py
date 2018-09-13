from troposphere import Equals, Join, Ref

from .template import template
from .utils import ParameterWithDefaults as Parameter

domain_name = Ref(template.add_parameter(
    Parameter(
        "DomainName",
        Description="The fully-qualified domain name for the application.",
        Type="String",
    ),
    group="Global",
    label="Domain Name",
))

domain_name_alternates = Ref(template.add_parameter(
    Parameter(
        "DomainNameAlternates",
        Description="A comma-separated list of Alternate FQDNs to be included in "
                    "the Subject Alternative Name extension of the SSL certificate.",
        Type="CommaDelimitedList",
    ),
    group="Global",
    label="Alternate Domain Names",
))

no_alt_domains = "NoAlternateDomains"
template.add_condition(
    no_alt_domains,
    # Equals() only supports strings, so convert domain_name_alternates to one first
    Equals(Join("", domain_name_alternates), ""),
)
