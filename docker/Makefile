PYTHON = python
PACKAGE_VERSION := $(shell $(PYTHON) -c 'import runpy; print(runpy.run_path("../nojava_ipmi_kvm/_version.py")["__version__"])')

default:
	@>&2 echo "No default target available, please select one of these: \"build-openjdk\", \"build-oracle\"."

build-openjdk:
	for openjdk_version in 7 8; do \
	    docker build -t "sciapp/nojava-ipmi-kvm:latest-openjdk-$${openjdk_version}" \
	                 -f "Dockerfile_openjdk-$${openjdk_version}" .; \
	done
	for openjdk_version in 7 8; do \
	    docker tag "sciapp/nojava-ipmi-kvm:latest-openjdk-$${openjdk_version}" \
	               "sciapp/nojava-ipmi-kvm:v$(PACKAGE_VERSION)-openjdk-$${openjdk_version}"; \
	done

build-oracle:
	@if [[ -f "jre-7u80-linux-x64.tar.gz" ]]; then \
	    docker build -t "sciapp/nojava-ipmi-kvm:latest-oraclejre-7" -f "Dockerfile_oraclejre-7" .; \
	    if [[ "$$(git symbolic-ref -q HEAD)" == "refs/heads/master" ]]; then \
	        docker tag "sciapp/nojava-ipmi-kvm:latest-oraclejre-7" \
	                   "sciapp/nojava-ipmi-kvm:v$(PACKAGE_VERSION)-oraclejre-7"; \
	    fi; \
	else \
	    >&2 echo "Please download \"jre-7u80-linux-x64.tar.gz\" to build an Oracle Java 7 docker image."; \
	fi; \
	if [[ -f "jre-8u251-linux-x64.tar.gz" ]]; then \
	    docker build -t "sciapp/nojava-ipmi-kvm:latest-oraclejre-8" -f "Dockerfile_oraclejre-8" .; \
	    if [[ "$$(git symbolic-ref -q HEAD)" == "refs/heads/master" ]]; then \
	        docker tag "sciapp/nojava-ipmi-kvm:latest-oraclejre-8" \
	                   "sciapp/nojava-ipmi-kvm:v$(PACKAGE_VERSION)-oraclejre-8"; \
	    fi; \
	else \
	    >&2 echo "Please download \"jre-8u251-linux-x64.tar.gz\" to build an Oracle Java 8 docker image."; \
	fi

.PHONY: build-openjdk build-oracle default
