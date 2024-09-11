arch=linux_$(shell uname -m)
#platname=linux_${arch}
#version=$(shell tr -d '\042' < pyproject.toml | sed -n '/^version = /{s/.* //;p;q}')
#package_name=dist/reliq-${version}-py3-none-any.whl

all: reliqc reliqpython

reliqc:
	make -C reliq-c clean lib -j4 CFLAGS='-O3'
	mv reliq-c/libreliq.so reliq/

reliqpython:
	python -m build

#python setup.py bdist_wheel --plat-name manylinux2014_${arch}

#python -m wheel tags --platform-tag ${platname} ${package_name}
#rm ${package_name}
