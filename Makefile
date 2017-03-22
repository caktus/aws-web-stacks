.DEFAULT_GOAL := templates

check:
	flake8 stack/

templates:
	mkdir -p content
	python -c 'import stack' > content/eb-no-nat.json
	USE_NAT_GATEWAY=on python -c 'import stack' > content/eb-nat.json
	USE_ECS=on python -c 'import stack' > content/ecs-no-nat.json
	USE_ECS=on USE_NAT_GATEWAY=on python -c 'import stack' > content/ecs-nat.json
	USE_GOVCLOUD=on python -c 'import stack' > content/gc-no-nat.json
	USE_GOVCLOUD=on USE_NAT_GATEWAY=on python -c 'import stack' > content/gc-nat.json

upload:
	aws s3 sync content/ s3://aws-container-basics/ --acl public-read
