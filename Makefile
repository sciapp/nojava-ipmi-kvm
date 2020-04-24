default:
	@>&2 echo "No default target available, please select one of these: \"build-openjdk\", \"build-oracle\"."

build-openjdk:
	$(MAKE) -C docker $@

build-oracle:
	$(MAKE) -C docker $@

.PHONY: build-openjdk build-oracle default
