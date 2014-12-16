# coding: utf-8

from lib.api import *  # noqa
from fabric.api import warn_only


class MariaDB:
    def __init__(self, root_password):
        self.root_password = root_password

    def install(self):
        package.register_repo(
            name='mariadb',
            baseurl='http://yum.mariadb.org/5.5/centos6-amd64',
            gpgkey='https://yum.mariadb.org/RPM-GPG-KEY-MariaDB',
        )

        package.install('MariaDB-server')

        is_updated = filer.template('/etc/my.cnf.d/server.cnf')

        service.enable('mysql')
        service.start('mysql')
        if is_updated:
            service.restart('mysql')

        with warn_only():
            result = run('mysql -uroot -p{0} -e "show status;"'.format(self.root_password))
            if result.return_code != 0:
                sudo('mysqladmin password {0} -uroot'.format(self.root_password))
                result = run('mysql -uroot -p{0} -e "show status;"'.format(self.root_password))

    def sql(self, query):
        return run('mysql -uroot -p{0} -e"{1}"'.format(self.root_password, query))

    def create_user(self, user, password, host='localhost',
                    privileges='ALL PRIVILEGES', table='*.*'):
        query = 'GRANT {privileges} ON {table} TO \'{user}\'@\'{host}\' IDENTIFIED BY \'{password}\''.format(
            privileges=privileges,
            table=table,
            user=user,
            password=password,
            host=host,
        )

        return self.sql(query)

    def create_database(self, database):
        with warn_only():
            result = self.sql('use {0}'.format(database))
            if result.return_code != 0:
                self.sql('CREATE DATABASE {0}'.format(database))
