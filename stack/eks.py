from troposphere import ec2, Ref, Tags, Join, iam, eks, Sub, GetAtt, Output

from .containers import (
    container_instance_role,
    container_volume_size,
    desired_container_instances,
    max_container_instances,
    container_instance_type,
)
from .template import template
from .vpc import (
    vpc,
    public_subnet_a,
    public_subnet_b,
    private_subnet_a,
    private_subnet_b,
)


# Subclass Nodegroup to fix type of tags
class CaktusNodegroup(eks.Nodegroup):
    props = dict(eks.Nodegroup.props, Tags=(dict, False),)


eks_service_role = iam.Role(
    # an IAM role that Kubernetes can assume to create AWS resources
    "EksServiceRole",
    template=template,
    AssumeRolePolicyDocument=dict(
        Statement=[
            dict(
                Effect="Allow",
                Principal=dict(Service=["eks.amazonaws.com"]),
                Action=["sts:AssumeRole"],
            )
        ]
    ),
    Path="/",
    ManagedPolicyArns=[
        "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
        "arn:aws:iam::aws:policy/AmazonEKSServicePolicy",
    ],
)


eks_security_group = ec2.SecurityGroup(
    "EksClusterSecurityGroup",
    template=template,
    GroupDescription="EKS control plane security group.",
    VpcId=Ref(vpc),
    Tags=Tags(Name=Join("-", [Ref("AWS::StackName"), "eks-cluster"]),),
)

cluster = eks.Cluster(
    "EksCluster",
    template=template,
    # Unlike most other resources in the stack, we hard-code the cluster name
    # both so it's easy to find and so it cannot be accidentally recreated
    # (for example if the ResourcesVpcConfig is changed).
    Name=Sub("${AWS::StackName}-cluster"),
    ResourcesVpcConfig=eks.ResourcesVpcConfig(
        SubnetIds=[
            # For load balancers
            Ref(public_subnet_a),
            Ref(public_subnet_b),
            # For worker nodes
            Ref(private_subnet_a),
            Ref(private_subnet_b),
        ],
        SecurityGroupIds=[Ref(eks_security_group),],
    ),
    RoleArn=GetAtt(eks_service_role, "Arn"),
)

CaktusNodegroup(
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-eks-nodegroup.html
    "Nodegroup",
    template=template,
    # For some reason, CloudFormation doesn't figure out that it needs to create
    # the cluster before the nodegroup that uses it.
    DependsOn=[cluster],
    # Required parameters:
    ClusterName=Ref(cluster),
    # The NodeRole must be specified as an ARN.
    NodeRole=GetAtt(container_instance_role, "Arn"),
    # The rest are optional.
    DiskSize=container_volume_size,
    InstanceTypes=[container_instance_type],
    ScalingConfig=eks.ScalingConfig(
        DesiredSize=desired_container_instances,
        MaxSize=max_container_instances,
        MinSize=2,
    ),
    Subnets=[Ref(private_subnet_a), Ref(private_subnet_b),],
    Tags=dict(),  # Have to provide a dict to force it not to be serialized as a Tags object would be
)

# OUTPUTS
template.add_output(
    [
        Output(
            "ClusterEndpoint",
            Description="The connection endpoint for the cluster API.",
            Value=GetAtt(cluster, "Endpoint.Address"),
        ),
    ]
)
