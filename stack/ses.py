from troposphere import iam

ses_policy = iam.Policy(
    PolicyName="SesAccessPolicy",
    PolicyDocument=dict(
        Statement=[dict(
            Effect="Allow",
            Action=[
                "ses:*",
            ],
            Resource="*",
        )],
    ),
)
