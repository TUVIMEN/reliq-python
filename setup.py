import os
import subprocess
import platform
from setuptools import setup
from setuptools.dist import Distribution
from setuptools.command.bdist_wheel import bdist_wheel
from setuptools.command.build import build


class BinaryDistribution(Distribution):
    def has_ext_modules(x):
        return True


def get_os():
    system = platform.system()
    if system.startswith("MINGW64_NT-"):
        return "windows"
    elif system == "Darwin":
        return "macos"
    elif system == "Linux":
        return "linux"


c_os = get_os()


def compile():
    others = []
    if c_os == "windows":
        others = ["LDFLAGS=/ucrt64/lib/libgnurx.a", "LIB_OTHERS=src/strptime.c"]
    subprocess.check_call(
        [
            "make",
            "-C",
            "reliq-c",
            "clean",
            "lib",
            "-j" + str(os.cpu_count()),
            'CFLAGS="-O3"',
            *others,
        ]
    )
    os.rename("reliq-c/libreliq.so", "reliq/libreliq.so")


class Build(build):
    def run(self):
        compile()
        super().run()


class BdistWheel(bdist_wheel):
    def get_tag(self):
        tags = super().get_tag()

        plat = tags[2]

        if c_os == "windows":
            plat = "win_amd64"
        elif c_os == "macos":
            plat = (
                "macosx_"
                + platform.mac_ver()[0].split(".")[0]
                + "_0_"
                + platform.machine()
            )
        elif c_os == "linux":
            plat = "manylinux2014_" + platform.machine()

        return (self.python_tag, self.python_tag, plat)


setup(
    distclass=BinaryDistribution,
    cmdclass={
        "build": Build,
        "bdist_wheel": BdistWheel,
    },
)
