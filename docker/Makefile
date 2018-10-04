PACKAGE_VERSION := $(shell python -c 'import runpy; print(runpy.run_path("../nojava_ipmi_kvm/_version.py")["__version__"])')

upload: build
	@[ "$$(git symbolic-ref -q HEAD)" == "refs/heads/master" ] || \
		{ echo "Uploading can only be done on the master branch."; exit 1; }
	docker login && \
	docker push "sciapp/nojava-ipmi-kvm:v$(PACKAGE_VERSION)" && \
	docker push "sciapp/nojava-ipmi-kvm:latest"

build:
	if [ "$$(git symbolic-ref -q HEAD)" == "refs/heads/master" ]; then \
		docker build -t "sciapp/nojava-ipmi-kvm:v$(PACKAGE_VERSION)" . ; \
	fi
	docker build -t "sciapp/nojava-ipmi-kvm:latest" .

.PHONY: build push
