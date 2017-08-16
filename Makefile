.DEFAULT_GOAL := templates

check:
	flake8 stack/

templates:
	mkdir -p content
	USE_EC2=on python -c 'import stack' > content/ec2-no-nat.json
	USE_EC2=on USE_NAT_GATEWAY=on python -c 'import stack' > content/ec2-nat.json
	USE_EB=on python -c 'import stack' > content/eb-no-nat.json
	USE_EB=on USE_NAT_GATEWAY=on python -c 'import stack' > content/eb-nat.json
	USE_ECS=on python -c 'import stack' > content/ecs-no-nat.json
	USE_ECS=on USE_NAT_GATEWAY=on python -c 'import stack' > content/ecs-nat.json
	USE_GOVCLOUD=on python -c 'import stack' > content/gc-no-nat.json
	USE_GOVCLOUD=on USE_NAT_GATEWAY=on python -c 'import stack' > content/gc-nat.json

upload:
	aws s3 sync content/ s3://aws-container-basics/ --acl public-read
