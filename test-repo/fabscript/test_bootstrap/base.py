# cording: utf-8

from fabkit import task, parallel
from fablib.test_bootstrap import Libvirt

libvirt = Libvirt()


@task
@parallel
def setup():
    libvirt.setup()
