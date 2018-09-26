upload: clean
	@[ "$$(git symbolic-ref -q HEAD)" == "refs/heads/master" ] || \
		{ echo "Uploading can only be done on the master branch."; exit 1; }
	python setup.py sdist && \
	python setup.py bdist_wheel --universal && \
	twine upload dist/*

clean:
	rm -rf build dist *.egg-info

.PHONY: clean upload
