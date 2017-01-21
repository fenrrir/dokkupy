import subprocess


class CommandError(Exception):
    pass


DEBUG = True


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

    @property
    def is_running(self):
        try:
            output = self.service.run('list').splitlines()[1:]
            if not output:
                return False

            for line in output:
                line = line.split()
                name = line[0]
                status = line[2]
                if name == self.name:
                    return status == 'running'
            return False
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
        self.service.run('destroy', self.name, input=self.name + '\n')
