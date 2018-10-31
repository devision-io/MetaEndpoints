VERSION=$(shell python metaendpoints/info.py)

init:
	python3 -m pip install -r requirements.txt

publish:
	echo $(VERSION)

	python3 setup.py sdist bdist_wheel
	python3 -m twine upload dist/*

	$(shell git tag $(VERSION))
	$(shell git push origin $(VERSION))

	rm -fr build dist .egg requests.egg-info

	python3 -m pip install metaendpoints --upgrade --no-cache
