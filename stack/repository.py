import awacs.ecr as ecr
from awacs.aws import Allow, AWSPrincipal, Policy, Statement
from troposphere import AWS_ACCOUNT_ID, AWS_REGION, Join, Output, Ref
from troposphere.ecr import Repository

from .common import arn_prefix
from .template import template

# Create an `ECR` docker repository
repository = Repository(
    "ApplicationRepository",
    template=template,
    # Do we need to specify a repository name? The stack name might not be
    # a valid repository name, and if we just leave it out, AWS will make one
    # up for us.
    # RepositoryName=Ref(AWS_STACK_NAME),
    # Allow all account users to manage images.
    RepositoryPolicyText=Policy(
        Version="2008-10-17",
        Statement=[
            Statement(
                Sid="AllowPushPull",
                Effect=Allow,
                Principal=AWSPrincipal(
                    [Join("", [arn_prefix, ":iam::", Ref(AWS_ACCOUNT_ID), ":root"])]
                ),
                Action=[
                    ecr.GetDownloadUrlForLayer,
                    ecr.BatchGetImage,
                    ecr.BatchCheckLayerAvailability,
                    ecr.PutImage,
                    ecr.InitiateLayerUpload,
                    ecr.UploadLayerPart,
                    ecr.CompleteLayerUpload,
                ],
            ),
        ],
    ),
    ImageScanningConfiguration={"ScanOnPush": "true"},
)


# Output ECR repository URL
template.add_output(
    Output(
        "RepositoryURL",
        Description="The docker repository URL",
        Value=Join(
            "",
            [
                Ref(AWS_ACCOUNT_ID),
                ".dkr.ecr.",
                Ref(AWS_REGION),
                ".amazonaws.com/",
                Ref(repository),
            ],
        ),
    )
)
