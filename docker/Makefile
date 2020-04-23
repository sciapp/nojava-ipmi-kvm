PACKAGE_VERSION := $(shell python -c 'import runpy; print(runpy.run_path("../nojava_ipmi_kvm/_version.py")["__version__"])')

default:
	@>&2 echo "No default target available, please select one of these: \"build\" \"build-oracle\", \"upload\"."

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

build-oracle:
	docker build -t "sciapp/nojava-ipmi-kvm:latest-oraclejre-8" -f "Dockerfile_oraclejre-8" .
	if [ "$$(git symbolic-ref -q HEAD)" == "refs/heads/master" ]; then \
	    docker tag "sciapp/nojava-ipmi-kvm:latest-oraclejre-8" \
	               "sciapp/nojava-ipmi-kvm:v$(PACKAGE_VERSION)-oraclejre-8"; \
	fi

upload: build
	@[ "$$(git symbolic-ref -q HEAD)" == "refs/heads/master" ] || \
		{ echo "Uploading can only be done on the master branch."; exit 1; }
	docker login docker.io && \
	for openjdk_version in 7 8; do \
	    docker push "sciapp/nojava-ipmi-kvm:v$(PACKAGE_VERSION)-openjdk-$${openjdk_version}" && \
	    docker push "sciapp/nojava-ipmi-kvm:latest-openjdk-$${openjdk_version}" || exit; \
	done

.PHONY: build build-oracle default upload
