# Copyright 2017 Rodrigo Pinheiro Marques de Araujo <fenrrir@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is furnished
# to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
# OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN
# AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH
# THE SOFTWARE OR THE USE OR OTHER

import os
import subprocess

from git import Repo


class CommandError(Exception):
    pass


DEBUG = os.environ.get('DOKKUPY_DEBUG', False)


class Command(object):
    def __init__(self, name, *params, **popen_kwargs):
        self.name = name
        self.params = params
        self.popen_kwargs = popen_kwargs

    def run(self, *params, **kwargs):
        cmd = self.get_command(*params)
        if DEBUG:
            print(cmd)

        input = kwargs.get('input')
        stdin = subprocess.PIPE if input else None
        p = subprocess.Popen(cmd,
                             stdin=stdin,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             **self.popen_kwargs)

        stdout, stderr = p.communicate(input)
        if p.returncode:
            if stderr:
                raise CommandError('Error: {}'.format(stderr))
            raise CommandError('Error: {}'.format(p.returncode))
        return stdout

    def get_command(self, *extra_params):
        return [self.name] + list(self.params) + list(extra_params)


class Dokku(Command):
    def __init__(self, hostname):
        super(Dokku, self).__init__('ssh',
                                    '-t',
                                    hostname)
        self.hostname = hostname

    def _list(self):
        output = self.run('apps')
        return output.splitlines()[1:]

    def __getitem__(self, app):
        return App(app, self)

    def __iter__(self):
        return iter(App(app, self) for app in iter(self._list()))

    def get_service(self, name):
        service = Service(name, self)
        if not service:
            raise CommandError('Service not found')
        return service


class App(object):
    def __init__(self, name, dokku):
        self.name = name
        self.dokku = dokku

    def create(self):
        self.dokku.run('apps:create', self.name)

    def __repr__(self):
        return 'App("{self.name}")'.format(self=self)

    def get_config(self):
        try:
            output = self.dokku.run('config', self.name)
            result = {}
            for line in output.splitlines()[1:]:
                key, value = line.split()
                result[key[:-1].strip()] = value.strip()
            return result
        except CommandError:
            return {}

    def set_config(self, key, value):
        config = '{key}={value}'.format(key=key, value=value)
        self.dokku.run('config:set', self.name, config)

    def del_config(self, key):
        self.dokku.run('config:unset', self.name, key)

    def destroy(self):
        self.dokku.run('apps:destroy', self.name, input=self.name + '\n')

    def __nonzero__(self):
        return bool([app for app in list(self.dokku) if app.name == self.name])

    def __bool__(self):
        return self.__nonzero__()

    @property
    def is_running(self):
        try:
            output = self.dokku.run('ps', self.name)
            if not output:
                return False
            return True
        except CommandError:
            return False

    def start(self):
        self.dokku.run('ps:start', self.name)

    def stop(self):
        self.dokku.run('ps:stop', self.name)

    def restart(self):
        self.dokku.run('ps:restart', self.name)

    def deploy(self, project_path=None, remote_name='dokkupy', current_branch=False, remote_url=None):
        if not project_path:
            project_path = os.getcwd()

        repo = Repo(project_path)

        if not remote_url:
            remote_url = self.dokku.hostname + ':' + self.name
        if remote_name not in [r.name for r in repo.remotes]:
            remote = repo.create_remote(remote_name, remote_url)
        else:
            remote = repo.remote(remote_name)
            remote.set_url(remote_url)

        if not current_branch:
            refspec = 'master:master'
        else:
            branch = repo.active_branch
            refspec = '{}:master'.format(branch)

        remote.push(refspec)


class Service(object):
    def __init__(self, name, dokku):
        self.name = name
        self.dokku = dokku

    def _subcommand(self, subcmd):
        return '{name}:{subcmd}'.format(name=self.name, subcmd=subcmd)

    def __repr__(self):
        return 'Service("{self.name})"'.format(self=self)

    def __nonzero__(self):
        try:
            self.dokku.run(self._subcommand('help'))
            return True
        except CommandError:
            return False

    def __bool__(self):
        return self.__nonzero__()

    def run(self, *args, **kwargs):
        return self.dokku.run(self._subcommand(args[0]), *args[1:], **kwargs)

    def __getitem__(self, instance_name):
        return ServiceInstance(instance_name, service=self)

    def _list(self):
        output = self.run('list')
        return [line.split()[0] for line in output.splitlines()[1:]]

    def __iter__(self):
        return iter(ServiceInstance(instance, self) for instance in iter(self._list()))


class ServiceInstance(object):
    def __init__(self, name, service):
        self.name = name
        self.service = service

    def __repr__(self):
        return '{service}("{self.name}")'.format(self=self, service=self.service.name.title())

    def __nonzero__(self):
        try:
            self.service.run('info', self.name)
            return True
        except CommandError:
            return False

    def __bool__(self):
        return self.__nonzero__()

    def _infolist(self):
        output = self.service.run('list').splitlines()[1:]
        empty = [None, None, None, None, None]

        if not output:
            return empty

        for line in output:
            line = line.split()
            name = line[0]
            if name == self.name:
                return line

        return empty

    @property
    def is_running(self):
        try:
            info = self._infolist()
            status = info[2]
            return status == 'running'
        except CommandError:
            return False

    def start(self):
        self.service.run('start', self.name)

    def stop(self):
        self.service.run('stop', self.name)

    def restart(self):
        self.service.run('restart', self.name)

    def clone(self, source):
        self.service.run('clone', source, self.name)

    def destroy(self):
        if self.is_running:
            self.stop()
        for app in self.links:
            if app:
                self.unlink(app)
        self.service.run('destroy', self.name, input=self.name + '\n')

    def link(self, app):
        self.service.run('link', self.name, app.name)

    def unlink(self, app):
        self.service.run('unlink', self.name, app.name)

    @property
    def links(self):
        output = self.service.run('info', self.name).splitlines()[1:]

        if not output:
            return []

        for line in output:
            line = line.split(':')
            name = line[0].strip()
            if name == 'Links':
                apps = line[1].split()
                return [App(name, self.service.dokku) for name in apps if name != '-']
        return []

    def create(self):
        self.service.run('create', self.name)
