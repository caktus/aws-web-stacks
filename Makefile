.DEFAULT_GOAL := templates

templates:
	mkdir -p content
	USE_EKS=on python -c 'import stack' > content/eks-no-nat.yaml
	USE_EKS=on USE_NAT_GATEWAY=on python -c 'import stack' > content/eks-nat.yaml
	USE_GOVCLOUD=on python -c 'import stack' > content/gc-no-nat.yaml
	USE_GOVCLOUD=on USE_NAT_GATEWAY=on python -c 'import stack' > content/gc-nat.yaml

versioned_templates: templates
	# version must be passed via the command-line, e.g., make VERSION=x.y.z versioned_templates
	set -e; cd content/; mkdir -p $(VERSION); for file in `ls *nat.yaml`; do cp $$file $(VERSION)/`echo $$file|cut -d'.' -f1`-$(VERSION).yaml; done

upload:
	aws s3 sync content/ s3://aws-web-stacks/ --acl public-read
