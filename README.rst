dokkupy - Python API and script for dokku
=========================================

Install ::

    pip install -e git+https://github.com/fenrrir/dokkupy.git

Requires ::

    'GitPython==2.1.0'

Features
--------
- API for apps
- API for addons/plugins


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
        mydb.create()
        mydb.link(first_app)
