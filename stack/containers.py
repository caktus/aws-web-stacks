"""
Common (almost) between instances, DOKKU, ECS, and EKS.
"""
from awacs import ecr
from troposphere import Ref, iam

from stack import USE_DOKKU, USE_EB, USE_ECS, USE_EKS
from stack.template import template
from stack.utils import ParameterWithDefaults as Parameter
from stack.assets import assets_management_policy
from stack.logs import logging_policy

if not USE_DOKKU and not USE_EB:
    desired_container_instances = Ref(
        template.add_parameter(
            Parameter(
                "DesiredScale",
                Description="Desired container instances count",
                Type="Number",
                Default="3" if USE_ECS else "2",
            ),
            group="Application Server",
            label="Desired Instance Count",
        )
    )
    max_container_instances = Ref(
        template.add_parameter(
            Parameter(
                "MaxScale",
                Description="Maximum container instances count",
                Type="Number",
                Default="3" if USE_ECS else "4",
            ),
            group="Application Server",
            label="Maximum Instance Count",
        )
    )

    if not USE_ECS:
        container_volume_size = Ref(
            template.add_parameter(
                Parameter(
                    "ContainerVolumeSize",
                    Description="Size of instance EBS root volume (in GB)",
                    Type="Number",
                    Default="20" if USE_EKS else "8",
                ),
                group="Application Server",
                label="Root Volume Size",
            )
        )

container_policies = [assets_management_policy, logging_policy]

if USE_ECS:
    container_policies.extend(
        [
            iam.Policy(
                PolicyName="ECSManagementPolicy",
                PolicyDocument=dict(
                    Statement=[
                        dict(
                            Effect="Allow",
                            Action=["ecs:*", "elasticloadbalancing:*"],
                            Resource="*",
                        )
                    ],
                ),
            ),
            iam.Policy(
                PolicyName="ECRManagementPolicy",
                PolicyDocument=dict(
                    Statement=[
                        dict(
                            Effect="Allow",
                            Action=[
                                ecr.GetAuthorizationToken,
                                ecr.GetDownloadUrlForLayer,
                                ecr.BatchGetImage,
                                ecr.BatchCheckLayerAvailability,
                            ],
                            Resource="*",
                        )
                    ],
                ),
            ),
        ]
    )

if not USE_EB:
    container_instance_role = iam.Role(
        "ContainerInstanceRole",
        template=template,
        AssumeRolePolicyDocument=dict(
            Statement=[
                dict(
                    Effect="Allow",
                    Principal=dict(Service=["ec2.amazonaws.com"]),
                    Action=["sts:AssumeRole"],
                )
            ]
        ),
        Path="/",
        Policies=container_policies,
        **(
            dict(
                ManagedPolicyArns=[
                    "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
                    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
                    "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
                ]
            )
            if USE_EKS
            else {}
        ),
    )

    container_instance_profile = iam.InstanceProfile(
        "ContainerInstanceProfile",
        template=template,
        Path="/",
        Roles=[Ref(container_instance_role)],
    )

container_instance_type = Ref(
    template.add_parameter(
        Parameter(
            "ContainerInstanceType",
            Description="The application server instance type",
            Type="String",
            Default="t2.micro",
            AllowedValues=[
                "t3.nano",
                "t3.micro",
                "t3.small",
                "t3.medium",
                "t3.large",
                "t3.xlarge",
                "t3.2xlarge",
                "t2.nano",
                "t2.micro",
                "t2.small",
                "t2.medium",
                "t2.large",
                "t2.xlarge",
                "t2.2xlarge",
                "m5.large",
                "m5.xlarge",
                "m5.2xlarge",
                "m5.4xlarge",
                "m5.12xlarge",
                "m5.24xlarge",
                "m5d.large",
                "m5d.xlarge",
                "m5d.2xlarge",
                "m5d.4xlarge",
                "m5d.12xlarge",
                "m5d.24xlarge",
                "m4.large",
                "m4.xlarge",
                "m4.2xlarge",
                "m4.4xlarge",
                "m4.10xlarge",
                "m4.16xlarge",
                "m3.medium",
                "m3.large",
                "m3.xlarge",
                "m3.2xlarge",
                "c5.large",
                "c5.xlarge",
                "c5.2xlarge",
                "c5.4xlarge",
                "c5.9xlarge",
                "c5.18xlarge",
                "c5d.large",
                "c5d.xlarge",
                "c5d.2xlarge",
                "c5d.4xlarge",
                "c5d.9xlarge",
                "c5d.18xlarge",
                "c4.large",
                "c4.xlarge",
                "c4.2xlarge",
                "c4.4xlarge",
                "c4.8xlarge",
                "c3.large",
                "c3.xlarge",
                "c3.2xlarge",
                "c3.4xlarge",
                "c3.8xlarge",
                "p2.xlarge",
                "p2.8xlarge",
                "p2.16xlarge",
                "g2.2xlarge",
                "g2.8xlarge",
                "x1.16large",
                "x1.32xlarge",
                "r5.large",
                "r5.xlarge",
                "r5.2xlarge",
                "r5.4xlarge",
                "r5.12xlarge",
                "r5.24xlarge",
                "r4.large",
                "r4.xlarge",
                "r4.2xlarge",
                "r4.4xlarge",
                "r4.8xlarge",
                "r4.16xlarge",
                "r3.large",
                "r3.xlarge",
                "r3.2xlarge",
                "r3.4xlarge",
                "r3.8xlarge",
                "i3.large",
                "i3.xlarge",
                "i3.2xlarge",
                "i3.4xlarge",
                "i3.8xlarge",
                "i3.16large",
                "d2.xlarge",
                "d2.2xlarge",
                "d2.4xlarge",
                "d2.8xlarge",
                "f1.2xlarge",
                "f1.16xlarge",
            ],
        ),
        group="Application Server",
        label="Instance Type",
    )
)
