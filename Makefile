all:	clean	install

build:
	python setup.py	build

install:
	python setup.py install

uninstall:
	pip uninstall web-bank-connect

clean:
	python setup.py clean
	rm -rf dist build *egg-info
	find . -name \*.pyc | xargs rm -f --
