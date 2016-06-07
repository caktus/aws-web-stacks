from troposphere.ecr import Repository

from .template import template


# Create an `ECR` docker repository
repository = Repository(
    "ApplicationRepository",
    template=template,
    RepositoryName="application",
)
