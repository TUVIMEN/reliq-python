from setuptools import setup
from setuptools.dist import Distribution


class BinaryDistribution(Distribution):
    def has_ext_modules(x):
        return True


setup(
    distclass=BinaryDistribution,
)
