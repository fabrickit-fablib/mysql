# cording: utf-8

from fabkit import task
from fablib.test_bootstrap import docker

bootstrap = docker.Docker()


@task
def setup():
    bootstrap.setup()
