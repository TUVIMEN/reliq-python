arch=linux_$(shell uname -m)

all: reliqc

reliqc:
	make -C reliq-c lib -j4 CFLAGS='-O3'
	mv reliq-c/libreliq.so reliq/
