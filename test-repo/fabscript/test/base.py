# coding: utf-8

from fabkit import task, serial
from fablib.mysql import MySQL


@task
def setup():
    mysql = MySQL()
    mysql.setup()


@task
@serial
def setup_replication():
    mysql = MySQL()
    mysql.setup_replication()
