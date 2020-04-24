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
	@[[ -f "jre-8u251-linux-x64.tar.gz" ]] || { \
	    >&2 echo "Please download Oracle Java first (\"jre-8u251-linux-x64.tar.gz\")."; \
	    exit 1; \
	}
	docker build -t "sciapp/nojava-ipmi-kvm:latest-oraclejre-8" -f "Dockerfile_oraclejre-8" .
	if [ "$$(git symbolic-ref -q HEAD)" == "refs/heads/master" ]; then \
	    docker tag "sciapp/nojava-ipmi-kvm:latest-oraclejre-8" \
	               "sciapp/nojava-ipmi-kvm:v$(PACKAGE_VERSION)-oraclejre-8"; \
	fi

.PHONY: build-openjdk build-oracle default
