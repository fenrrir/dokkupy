dokkupy - Python API and script for dokku
=========================================

Install ::

    pip install -e git+https://github.com/fenrrir/dokkupy.git

Requires ::

    'GitPython==2.1.0'

Debugging ::

    export DOKKUPY_DEBUG=1

Features
--------
- API for apps
    - list
    - create
    - exists
    - is_running
    - start
    - stop
    - restart
    - destroy
    - get_config
    - set_config
    - del_config
    - scale

- API for addons/plugins
    - list
    - create
    - exists
    - is_running
    - start
    - stop
    - restart
    - clone
    - destroy
    - link
    - unlink
    - links


Examples
--------

Stopping a application ::

    dokku = dokkupy.Dokku('dokku@mydokkuhost.net')
    apps = list(dokku)
    first_app = apps[0]
    first_app.stop()


Creating a postgres database ::

    dokku = dokkupy.Dokku('dokku@mydokkuhost.net')
    postgres = dokku.get_service('postgres')
    if postgres:  # is available?
        mydb = postgres['mydb']
        if mydb: # database exists
            mydb.destroy()
        mydb.create()
        mydb.link(first_app)



Deploying with cli ::

    $ cat config-example.json
    {
      "services": [
        {
          "name": "postgres",
          "destroy_on_remove": true
        }
      ],
      "environ": {
        "key": "secret"
      },
      "scale": {
        "worker": 1
    }
    $ cd <project path>
    $ dokkupycli --project-name mydeploy --config config-example.json --address dokku@mydokkuhost.net create
