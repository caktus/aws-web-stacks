import os

from troposphere import elasticloadbalancing as elb
from troposphere import Equals, GetAtt, If, Join, Output, Parameter, Ref

from .security_groups import load_balancer_security_group
from .template import template
from .vpc import loadbalancer_a_subnet, loadbalancer_b_subnet

web_worker_health_check = Ref(template.add_parameter(Parameter(
    "WebWorkerHealthCheck",
    Description="Web worker health check URL path, e.g., \"/health-check\"; "
                "will default to TCP-only health check if left blank",
    Type="String",
    Default="",
)))


if os.environ.get('USE_ECS') == 'on':
    web_worker_port = Ref(template.add_parameter(Parameter(
        "WebWorkerPort",
        Description="Web worker container exposed port",
        Type="Number",
        Default="8000",
    )))
else:
    # default to port 80 for EC2 and Elastic Beanstalk options
    web_worker_port = Ref(template.add_parameter(Parameter(
        "WebWorkerPort",
        Description="Default web worker exposed port (non-HTTPS)",
        Type="Number",
        Default="80",
    )))


web_worker_protocol = Ref(template.add_parameter(Parameter(
    "WebWorkerProtocol",
    Description="Web worker instance protocol",
    Type="String",
    Default="HTTP",
    AllowedValues=["HTTP", "HTTPS"],
)))

tcp_health_check_condition = "TcpHealthCheck"
template.add_condition(
    tcp_health_check_condition,
    Equals(web_worker_health_check, ""),
)

# Web load balancer

listeners = [
    elb.Listener(
        LoadBalancerPort=80,
        InstanceProtocol=web_worker_protocol,
        InstancePort=web_worker_port,
        Protocol='HTTP',
    )
]

if os.environ.get('USE_GOVCLOUD') == 'on':
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
    listeners.append(elb.Listener(
        LoadBalancerPort=443,
        InstanceProtocol=web_worker_protocol,
        InstancePort=web_worker_port,
        Protocol='HTTPS',
        SSLCertificateId=application_certificate,
    ))

load_balancer = elb.LoadBalancer(
    'LoadBalancer',
    template=template,
    Subnets=[
        Ref(loadbalancer_a_subnet),
        Ref(loadbalancer_b_subnet),
    ],
    SecurityGroups=[Ref(load_balancer_security_group)],
    Listeners=listeners,
    HealthCheck=elb.HealthCheck(
        Target=If(
            tcp_health_check_condition,
            Join("", ["TCP:", web_worker_port]),
            Join("", [
                web_worker_protocol,
                ":",
                web_worker_port,
                web_worker_health_check,
            ]),
        ),
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
