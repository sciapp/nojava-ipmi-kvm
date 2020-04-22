PACKAGE_VERSION := $(shell python -c 'import runpy; print(runpy.run_path("../nojava_ipmi_kvm/_version.py")["__version__"])')

upload: build
	@[ "$$(git symbolic-ref -q HEAD)" == "refs/heads/master" ] || \
		{ echo "Uploading can only be done on the master branch."; exit 1; }
	docker login docker.io && \
	for openjdk_version in 7 8; do \
	    docker push "sciapp/nojava-ipmi-kvm:v$(PACKAGE_VERSION)-openjdk-$${openjdk_version}" && \
	    docker push "sciapp/nojava-ipmi-kvm:latest-openjdk-$${openjdk_version}" || exit; \
	done

build:
	for openjdk_version in 7 8; do \
	    docker build -t "sciapp/nojava-ipmi-kvm:latest-openjdk-$${openjdk_version}" \
	                 -f "Dockerfile_openjdk-$${openjdk_version}" .; \
	done
	if [ "$$(git symbolic-ref -q HEAD)" == "refs/heads/master" ]; then \
	    for openjdk_version in 7 8; do \
	        docker tag "sciapp/nojava-ipmi-kvm:latest-openjdk-$${openjdk_version}" \
	                   "sciapp/nojava-ipmi-kvm:v$(PACKAGE_VERSION)-openjdk-$${openjdk_version}"; \
	    done; \
	fi

.PHONY: build push
