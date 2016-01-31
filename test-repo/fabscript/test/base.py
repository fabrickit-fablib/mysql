# coding: utf-8

from fabkit import task
from fablib.sample import Sample

sample = Sample()


@task
def setup():
    sample.setup()
