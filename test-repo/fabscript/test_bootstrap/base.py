# cording: utf-8

from fabkit import task
from fablib.test_bootstrap import Libvirt

libvirt = Libvirt()


@task
def setup():
    libvirt.setup()
