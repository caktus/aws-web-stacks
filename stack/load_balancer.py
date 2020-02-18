from troposphere import elasticloadbalancing as elb
from troposphere import GetAtt, If, Join, Output, Ref

from . import USE_ECS, USE_GOVCLOUD
from .security_groups import load_balancer_security_group
from .template import template
from .utils import ParameterWithDefaults as Parameter
from .vpc import public_subnet_a, public_subnet_b

# Web worker

if USE_ECS:
    web_worker_port = Ref(template.add_parameter(
        Parameter(
            "WebWorkerPort",
            Description="Web worker container exposed port",
            Type="Number",
            Default="8000",
        ),
        group="Load Balancer",
        label="Web Worker Port",
    ))
else:
    # default to port 80 for EC2 and Elastic Beanstalk options
    web_worker_port = Ref(template.add_parameter(
        Parameter(
            "WebWorkerPort",
            Description="Default web worker exposed port (non-HTTPS)",
            Type="Number",
            Default="80",
        ),
        group="Load Balancer",
        label="Web Worker Port",
    ))

web_worker_protocol = Ref(template.add_parameter(
    Parameter(
        "WebWorkerProtocol",
        Description="Web worker instance protocol",
        Type="String",
        Default="HTTP",
        AllowedValues=["HTTP", "HTTPS"],
    ),
    group="Load Balancer",
    label="Web Worker Protocol",
))

# Web worker health check

web_worker_health_check_protocol = Ref(template.add_parameter(
    Parameter(
        "WebWorkerHealthCheckProtocol",
        Description="Web worker health check protocol",
        Type="String",
        Default="TCP",
        AllowedValues=["TCP", "HTTP", "HTTPS"],
    ),
    group="Load Balancer",
    label="Health Check: Protocol",
))

web_worker_health_check_port = Ref(template.add_parameter(
    Parameter(
        "WebWorkerHealthCheckPort",
        Description="Web worker health check port",
        Type="Number",
        Default="80",
    ),
    group="Load Balancer",
    label="Health Check: Port",
))

web_worker_health_check = Ref(template.add_parameter(
    Parameter(
        "WebWorkerHealthCheck",
        Description="Web worker health check URL path, e.g., \"/health-check\"; "
                    "required unless WebWorkerHealthCheckProtocol is TCP",
        Type="String",
        Default="",
    ),
    group="Load Balancer",
    label="Health Check: URL",
))

# Web load balancer

listeners = [
    elb.Listener(
        LoadBalancerPort=80,
        InstanceProtocol=web_worker_protocol,
        InstancePort=web_worker_port,
        Protocol='HTTP',
    )
]

if USE_GOVCLOUD:
    # configure the default HTTPS listener to pass TCP traffic directly,
    # since GovCloud doesn't support the Certificate Manager (this can be
    # modified to enable SSL termination at the load balancer via the AWS
    # console, if needed)
    listeners.append(elb.Listener(
        LoadBalancerPort=443,
        InstanceProtocol='TCP',
        InstancePort=443,
        Protocol='TCP',
    ))
else:
    from .certificates import application as application_certificate
    from .certificates import cert_condition
    listeners.append(If(cert_condition, elb.Listener(
        LoadBalancerPort=443,
        InstanceProtocol=web_worker_protocol,
        InstancePort=web_worker_port,
        Protocol='HTTPS',
        SSLCertificateId=application_certificate,
    ), Ref("AWS::NoValue")))

load_balancer = elb.LoadBalancer(
    'LoadBalancer',
    template=template,
    Subnets=[
        Ref(public_subnet_a),
        Ref(public_subnet_b),
    ],
    SecurityGroups=[Ref(load_balancer_security_group)],
    Listeners=listeners,
    HealthCheck=elb.HealthCheck(
        Target=Join("", [
            web_worker_health_check_protocol,
            ":",
            web_worker_health_check_port,
            web_worker_health_check,
        ]),
        HealthyThreshold="2",
        UnhealthyThreshold="2",
        Interval="100",
        Timeout="10",
    ),
    CrossZone=True,
)

template.add_output(Output(
    "LoadBalancerDNSName",
    Description="Loadbalancer DNS",
    Value=GetAtt(load_balancer, "DNSName")
))

template.add_output(Output(
    "LoadBalancerHostedZoneID",
    Description="Loadbalancer hosted zone",
    Value=GetAtt(load_balancer, "CanonicalHostedZoneNameID")
))
