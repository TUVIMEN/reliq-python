all: reliqc reliqpython

reliqc:
	make -C reliq-c clean lib -j4 CFLAGS='-O3'
	mv reliq-c/libreliq.so reliq/

reliqpython:
	python -m build
