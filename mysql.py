# coding: utf-8

import re
import socket
from fabkit import *  # noqa
from fablib.base import SimpleBase


class MySQL(SimpleBase):
    def __init__(self):
        self.data_key = 'mysql'
        self.data = {
            'port': 3306,
            'user_map': {},
            'phpmyadmin': {
                'enable': False
            }
        }

        self.services = {
            'CentOS Linux 7.*': [
                'mysql',
            ],
            'Ubuntu 14.*': [
                'mysql',
            ],
        }

        self.packages = {
            'CentOS Linux 7.*': [
                {
                    'name': 'mysql-community-release',
                    'path': 'http://dev.mysql.com/get/mysql-community-release-el7-5.noarch.rpm',
                },
                'mysql-community-server',
            ],
            'Ubuntu 14.*': [
                'mysql-server-5.6',
            ]
        }

    def init_after(self):
        for cluster in self.data.get('cluster_map', {}).values():
            if env.host in cluster['hosts']:
                self.data.update(cluster)
                break

        self.data['server_id'] = self.data['hosts'].index(env.host)
        self.data['auto_increment_offset'] = self.data['server_id'] + 1

        phpmyadmin = self.data['phpmyadmin']
        if phpmyadmin['enable']:
            self.packages['CentOS Linux 7.*'].extend([
                'httpd',
                'php',
                'epel-release',
                'phpMyAdmin',
                'php-mysql',
                'php-mcrypt',
            ])
            self.services['CentOS Linux 7.*'].append('httpd')
            self.update_packages()
            self.update_services()

    def setup(self):
        data = self.init()

        if self.is_tag('package'):
            if self.is_ubuntu():
                # sudo('add-apt-repository -y ppa:ondrej/mysql-5.6')
                sudo('apt-get update -y')

                # ubuntuだとmysql-serverインストール時にroot パスワードを入力させられるのを回避する
                # http://stackoverflow.com/questions/7739645/install-mysql-on-ubuntu-without-password-prompt
                sudo("debconf-set-selections <<< "
                     "'mysql-server mysql-server/root_password password tmppass'")
                sudo("debconf-set-selections <<< "
                     "'mysql-server mysql-server/root_password_again password tmppass'")

            Package('mariadb-config').uninstall()
            Package('mariadb-libs').uninstall()
            Package('mariadb-devel').uninstall()
            Package('mariadb-common').uninstall()

            self.install_packages()

        if self.is_tag('conf'):

            filer.mkdir('/etc/mysql')
            if filer.template('/etc/my.cnf', data=data):
                self.handlers['restart_mysqld'] = True
                self.handlers['restart_mysql'] = True
            if data['phpmyadmin']['enable']:
                if filer.template('/etc/httpd/conf.d/phpMyAdmin.conf',
                                  data=data['phpmyadmin']):
                    self.handlers['restart_httpd'] = True

        if self.is_tag('service'):
            self.enable_services().start_services()
            self.exec_handlers()

        if self.is_tag('data'):
            # init root_password
            if not filer.exists('/root/.my.cnf'):
                root_password = sudo('cat /dev/urandom | tr -dc "[:alnum:]" | head -c 32')
                if self.is_ubuntu():
                    sudo('mysqladmin password {0} -uroot -ptmppass'.format(root_password))
                else:
                    sudo('mysqladmin password {0} -uroot'.format(root_password))
                filer.template('/root/.my.cnf', data={'root_password': root_password})

            self.create_users()
            self.delete_default_users()

    def setup_replication(self):
        data = self.init()
        repl = data['replication']
        types = repl['types']
        repl_type = 'master'
        master_ip = None
        master_len = 0

        for index, host in enumerate(data['hosts']):
            if types[index] == 'master':
                master_len += 1
            if env.host != host and types[index] == 'master' and master_ip is None:
                master_ip = socket.gethostbyname(host)
            if env.host == host:
                repl_type = types[index]

        if master_ip is None:
            return

        if repl_type == 'master' and master_len < 2:
            return

        slave_user = data['user_map']['slave']
        result = self.sql('show slave status')
        if result.find(master_ip) == -1:
            self.sql("change master to "
                     "master_host = '{master_ip}', "
                     "master_port={port}, "
                     "master_user='{slave_user[user]}', "
                     "master_password='{slave_user[password]}', "
                     "master_auto_position=1;".format(
                         master_ip=master_ip, port=data['port'], slave_user=slave_user))

            self.sql("start slave")

    def sql(self, query):
        self.init()
        if self.is_ubuntu():
            return sudo('mysql -uroot '
                        '-p`grep ^password /root/.my.cnf | head -1 | awk \'{{print $3}}\'` '
                        '-e"{0}"'.format(query))
        else:
            return sudo('mysql -uroot '
                        '-e"{0}"'.format(query))

    def create_users(self):
        data = self.init()
        for user in data['user_map'].values():
            for db in user.get('dbs', ['*']):
                if env.host == data['server_id'] == 0:
                    self.sql('CREATE DATABASE IF NOT EXISTS {0};'.format(db))

                for src_host in user.get('src_hosts', ['localhost']):
                    query = 'GRANT {privileges} ON {table} TO \'{user}\'@\'{host}\' IDENTIFIED BY \'{password}\''.format(  # noqa
                        privileges=user.get('privileges', 'ALL PRIVILEGES'),
                        table='{0}.*'.format(db),
                        user=user['user'],
                        password=user['password'],
                        host=src_host,
                    )

                    self.sql(query)

    def delete_default_users(self):
        self.init()
        self.sql("delete from mysql.user where user='root' and host!='localhost'")
        self.sql("delete from mysql.user where user=''")

    def is_ubuntu(self):
        if re.match('Ubuntu.*', env.node['os']):
            return True
        return False
