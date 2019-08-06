.DEFAULT_GOAL := templates

check:
	flake8 stack/
	isort --recursive --check-only --diff stack/

templates:
	mkdir -p content
	USE_EC2=on python -c 'import stack' > content/ec2-no-nat.yaml
	USE_EC2=on USE_NAT_GATEWAY=on python -c 'import stack' > content/ec2-nat.yaml
	USE_EB=on python -c 'import stack' > content/eb-no-nat.yaml
	USE_EB=on USE_NAT_GATEWAY=on python -c 'import stack' > content/eb-nat.yaml
	USE_ECS=on python -c 'import stack' > content/ecs-no-nat.yaml
	USE_ECS=on USE_NAT_GATEWAY=on python -c 'import stack' > content/ecs-nat.yaml
	USE_DOKKU=on python -c 'import stack' > content/dokku-no-nat.yaml
	# USE_DOKKU=on USE_NAT_GATEWAY=on python -c 'import stack' > content/dokku-nat.yaml (disabled; need to SSH to instance to deploy)
	USE_GOVCLOUD=on python -c 'import stack' > content/gc-no-nat.yaml
	USE_GOVCLOUD=on USE_NAT_GATEWAY=on python -c 'import stack' > content/gc-nat.yaml
	cd content/; mkdir -p `cat ../version.txt`; for file in `ls *nat.yaml`; do cp $$file `cat ../version.txt`/`echo $$file|cut -d'.' -f1`-`cat ../version.txt`.yaml; done

upload:
	aws s3 sync content/ s3://aws-web-stacks/ --acl public-read
