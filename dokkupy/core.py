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
import sys
import json
import subprocess

from git import Repo, RemoteProgress


PY3 = sys.version_info.major == 3


class CommandError(Exception):
    pass


DEBUG = os.environ.get('DOKKUPY_DEBUG', False)


class GitProgress(RemoteProgress):
    def line_dropped(self, line):
        self.log(line)

    def update(self, *args):
        self.log(self._cur_line)

    def new_message_handler(self):
        def handler(line):
            self.log(line)

            if 'failed to push' in line:
                raise CommandError('failed to push')

        return handler

    def log(self, line):
        sys.stdout.write(line)


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

        if input and PY3:
            input = input.encode(sys.getdefaultencoding())

        stdin = subprocess.PIPE if input else None

        p = subprocess.Popen(cmd,
                             stdin=stdin,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             **self.popen_kwargs)

        stdout, stderr = p.communicate(input)
        if p.returncode:
            if stderr:
                if DEBUG:
                    print(stdout)
                raise CommandError('Error: {}'.format(stderr))
            raise CommandError('Error: {}'.format(p.returncode))

        if PY3:
            stdout = stdout.decode(sys.getdefaultencoding())
        return stdout

    def get_command(self, *extra_params):
        return [self.name] + list(self.params) + list(extra_params)


class Dokku(Command):
    def __init__(self, hostname=None):
        if hostname:
            cmd = ['ssh', '-t', hostname]
            self.hostname = hostname
        else:
            cmd = ['dokku']
        super(Dokku, self).__init__(*cmd)

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

    def deploy(self, name, config):
        app = self[name]

        if not app:
            app.create()

        for opts in config.get('services', []):
            service_factory = self.get_service(opts['name'])
            instance = service_factory[name + opts.get('suffix', '')]

            if instance:
                if opts.get('always_create'):
                    instance.destroy()

                    if opts.get('clone'):
                        instance.clone(opts['clone'])
                    else:
                        instance.create()

                if app.name not in [a.name for a in instance.links]:
                    instance.link(app)

                if not instance.is_running:
                    instance.start()
            else:
                if opts.get('clone'):
                    instance.clone(opts['clone'])
                else:
                    instance.create()

                if app.name not in [a.name for a in instance.links]:
                    instance.link(app)

        if config.get('environ'):
            for key, value in config['environ'].items():
                app.set_config(key, value)

        if config.get('scale'):
            scale = config.get('scale')
            if scale != app.get_scale():
                app.set_scale(**scale)

        app.deploy(project_path=config.get('path'), current_branch=config.get('current_branch', False))

        for command in config.get('commands', []):
            app.run(command)

    def remove(self, name, config):
        app = self[name]

        if app.is_running:
            app.stop()

        for opts in config.get('services', []):
            service_factory = self.get_service(opts['name'])
            instance = service_factory[name + opts.get('suffix', '')]

            if instance:
                if opts.get('destroy_on_remove'):
                    instance.destroy()

                if opts.get('stop_on_remove'):
                    instance.stop()

        if app:
            app.destroy()

    def deploy_from_file(self, name, filename):
        data = self._load_json(filename)
        self.deploy(name, data)

    def remove_from_file(self, name, filename):
        data = self._load_json(filename)
        self.remove(name, data)

    def _load_json(self, filename):
        with open(filename) as f:
            return json.load(f)


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

    def set_scale(self, **opts):
        opts = ['{}={}'.format(k, v) for k,v in opts.items()]
        self.dokku.run('ps:scale', self.name, *opts)

    def get_scale(self):
        output = self.dokku.run('ps:scale', self.name).splitlines()[3:]
        result = {}
        for line in output:
            try:
                proc, count = line[len('-----> '):].split()
                count = int(count)
                result[proc] = count
            except ValueError:
                pass
        return result

    def run(self, cmd):
        return self.dokku.run('run', self.name, *cmd.split())

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

        if DEBUG:
            progress = GitProgress()
        else:
            progress = None

        if DEBUG:
            print('deploying...')

        remote.push(refspec, progress=progress)


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
                self.unlink(app, force=True)
        self.service.run('destroy', self.name, input=self.name + '\n')

    def link(self, app):
        self.service.run('link', self.name, app.name)

    def unlink(self, app, force=False):
        try:
            self.service.run('unlink', self.name, app.name)
        except CommandError as error:
            if not force:
                raise error

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
