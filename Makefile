default:
	@>&2 echo "No default target available, please select one of these: \"build-openjdk\", \"build-oracle\" or \"build-html5\"."

build-openjdk:
	$(MAKE) -C docker $@

build-oracle:
	$(MAKE) -C docker $@

build-html5:
	$(MAKE) -C docker $@

.PHONY: build-openjdk build-oracle build-html5 default
