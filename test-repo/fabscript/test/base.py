# coding: utf-8

from fabkit import task
from fablib.mysql import MySQL

mysql = MySQL()


@task
def setup():
    mysql.setup()
