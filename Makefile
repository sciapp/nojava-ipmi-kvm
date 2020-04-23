default:
	@>&2 echo "No default target available, please select one of these: \"build-oracle\", \"clean\" \"upload\", \"upload-docker\"."

build-oracle:
	$(MAKE) -C docker build-oracle

upload: clean upload-docker
	@[ "$$(git symbolic-ref -q HEAD)" == "refs/heads/master" ] || \
		{ echo "Uploading can only be done on the master branch."; exit 1; }
	python3 setup.py sdist && \
	python3 setup.py bdist_wheel && \
	twine upload dist/*

upload-docker:
	$(MAKE) -C docker upload

clean:
	rm -rf build dist *.egg-info

.PHONY: build-oracle clean default upload-docker upload
