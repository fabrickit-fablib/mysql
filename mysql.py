# coding: utf-8

from fabkit import Service, Package, env, filer, run, api, sudo


class MySQL:
    def __init__(self):
        self.key = 'mysql'
        self.mysqld = Service('mysqld')
        self.is_init = False

        self.data = {
            'root_password': 'rootpass',
            'port': 3306,
            'users': {},
            'databases': {},
        }

    def get_init_data(self):
        if not self.is_init:
            if self.key in env.cluster:
                self.data.update(env.cluster[self.key])
            self.is_init = True

        return self.data

    def setup(self):
        data = self.get_init_data()

        Package('mysql').install()
        Package('mysql-server').install()
        is_updated = filer.template('/etc/my.cnf', data=data)

        self.mysqld.enable().start()
        if is_updated:
            self.mysqld.restart()

        # setup root user
        with api.warn_only():
            result = run('mysql -uroot -p{0} -e "show status;"'.format(data['root_password']))
            if result.return_code != 0:
                sudo('mysqladmin password {0} -uroot'.format(data['root_password']))
                result = run('mysql -uroot -p{0} -e "show status;"'.format(data['root_password']))

        self.create_users()
        self.create_databases()

    def sql(self, query):
        data = self.get_init_data()
        return run('mysql -uroot -p{0} -e"{1}"'.format(data['root_password'], query))

    def create_users(self):
        data = self.get_init_data()
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

        return self.sql(query)

    def create_databases(self):
        data = self.get_init_data()
        with api.warn_only():
            for dbname in data['databases']:
                result = self.sql('use {0}'.format(dbname))
                if result.return_code != 0:
                    self.sql('CREATE DATABASE {0}'.format(dbname))
