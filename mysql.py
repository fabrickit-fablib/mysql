# coding: utf-8

from fabkit import filer, api, sudo
from fablib.base import SimpleBase


class MySQL(SimpleBase):
    def __init__(self):
        self.data_key = 'mysql'
        self.services = {
            'CentOS Linux 7.*': ['mysqld'],
        }
        self.packages = {
            'CentOS Linux 7.*': [
                {
                    'name': 'mysql-community-release',
                    'path': 'http://dev.mysql.com/get/mysql-community-release-el7-5.noarch.rpm',
                },
                'mysql-community-server',
            ],
        }

        self.data = {
            'port': 3306,
            'users': {},
            'databases': {},
        }

    def setup(self):
        data = self.init()
        self.install_packages()

        filer.mkdir('/etc/mysql')
        is_updated = filer.template('/etc/mysql/my.cnf', data=data)

        self.enable_services().start_services()
        if is_updated:
            self.restart_services()

        # get root_password or init root_password
        if filer.exists('/root/.my.cnf'):
            root_password = sudo("grep ^password /root/.my.cnf | head -1 | awk '{print $3}'")
        else:
            root_password = sudo('cat /dev/urandom | tr -dc "[:alnum:]" | head -c 32')
            sudo('mysqladmin password {0} -uroot'.format(root_password))
            filer.template('/root/.my.cnf', data={'root_password': root_password})

        self.create_users()
        self.create_databases()

    def sql(self, query):
        self.init()
        return sudo('mysql -uroot -e"{0}"'.format(query))

    def create_users(self):
        data = self.init()
        for username, user in data['users'].items():
            for dbname, db in data['databases'].items():
                if db.get('user') == username:
                    query = 'GRANT {privileges} ON {table} TO \'{user}\'@\'{host}\' IDENTIFIED BY \'{password}\''.format(  # noqa
                        privileges=user.get('privileges', 'ALL PRIVILEGES'),
                        table='{0}.*'.format(dbname),
                        user=username,
                        password=user['password'],
                        host=user.get('host', 'localhost'),
                    )

                    self.sql(query)

    def create_databases(self):
        data = self.init()
        with api.warn_only():
            for db in data['databases'].values():
                result = self.sql('use {0}'.format(db['dbname']))
                if result.return_code != 0:
                    self.sql('CREATE DATABASE {0} DEFAULT CHARACTER SET utf8;'.format(db['dbname']))
