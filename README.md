# fablib mysql

## Example Attributes

``` yaml
mysql:
  root_password: rootpass
  users:
    openstack:
      password: openstackpass
      host: localhost
      privileges: ALL PRIVILEGES
  databases:
    keystone: 
      user: openstack
    nova: 
      user: openstack
    cinder: 
      user: openstack
```
