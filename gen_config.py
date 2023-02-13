import hashlib
import re
import dhall
import pathlib

SECRET = dhall.load(open('secret.dhall'))
CONFIG = dhall.load(open('config.dhall'))
TEMPLATE_REGEX = re.compile('{{(.*?)}}', re.MULTILINE|re.DOTALL)

def _flatten(l: list) -> list:
    return [el for sub in l for el in sub]

def get_mounts() -> list[str]:
    return _flatten([app['mounts'] for app in CONFIG['apps']])

class Mount:
    def __init__(self, name: str, src: str, dst: str):
        self.name = name
        self.src = pathlib.PurePath(src)
        self.dst = pathlib.PurePath(dst)

    def __repr__(self) -> str:
        return 'Mount {}: src={}, dst={}'.format(self.name, self.src, self.dst)

    def get(name: str) -> 'Mount':
        try:
            return next(
                mount for mount in Mount.all
                if mount.name == name
            )
        except:
            raise Exception('no such mount "' + name + '"')

Mount.all = [
    Mount(name=mount['name'], src=mount['src'], dst=mount['dst'])
    for mount in get_mounts()
]

def eval_template(template: str) -> str:
    def do_eval(match: re.Match) -> str:
        return str(eval(match.group(1)))
    return re.sub(TEMPLATE_REGEX, do_eval, template)

class CopyFile:
    def __init__(self, app_dir: pathlib.PurePath, name: str, src: str, templated: bool):
        self.name = name
        self.src = pathlib.PurePath(src)
        self.dst = pathlib.PurePath(app_dir) / self.src.name

        self.template_src = None
        self.templated = templated
        if self.templated:
            self.template_src = self.src
            build_hash = hashlib.md5()
            build_hash.update(str(pathlib.Path(self.src).resolve()).encode('utf-8'))
            digest = build_hash.hexdigest()
            self.src = pathlib.PurePath('build') / (digest + self.name)

    def __repr__(self) -> str:
        return 'CopyFile {}: {}{} -> {}'.format(
            self.name,
            str(self.src),
            ' ({})'.format(self.template_src) if self.templated else '',
            str(self.dst),
        )

    def get(name: str) -> 'CopyFile':
        try:
            return next(copied for copied in CopyFile.all if copied.name == name)
        except:
            raise Exception('no such copy file "' + name + '"')


    def do_template(self):
        if not self.templated:
            raise Exception('do_template called on non-templated file')

        build_dir = pathlib.Path('build')
        if not build_dir.exists():
            build_dir.mkdir()

        file = open(self.template_src)
        contents = str(file.read())
        file.close()

        new_contents = eval_template(contents)

        file = open(self.src, 'w+')
        file.write(new_contents)
        file.close()

class App:
    def __init__(
        self,
        name: str,
        app_dir: str,
        var_dir: str,
        log_dir: str,
        mount_dir: str,
        mounts: list[Mount],
        copied: list[CopyFile],
    ):
        self.name = name
        self.app_dir = pathlib.PurePath(app_dir)
        self.var_dir = pathlib.PurePath(var_dir)
        self.log_dir = pathlib.PurePath(log_dir)
        self.mount_dir = pathlib.PurePath(mount_dir)
        self.mounts = mounts
        self.copied = copied

    def __repr__(self) -> str:
        return 'App {}: app_dir={} var_dir={} log_dir={} mount_dir={} mounts={} copied={}'.format(
            self.name,
            self.app_dir,
            self.var_dir,
            self.log_dir,
            self.mount_dir,
            self.mounts,
            self.copied
        )

    def get(name: str) -> 'App':
        try:
            return next(
                app for app in App.all
                if app.name == name
            )
        except:
            raise Exception('no such app "' + name + '"')

    def get_copied(self, name: str) -> CopyFile:
        try:
            return next(copied for copied in self.copied if copied.name == name)
        except:
            raise Exception('no such copy file "' + name + '" for app "' + self.name + '"')

    def get_templated(self) -> list[CopyFile]:
        return [copied for copied in self.copied if copied.templated]

    def create_copy_commands(self) -> list[str]:
        commands = []
        for copied in self.copied:
            commands.append('COPY {} {}'.format(copied.src, copied.dst))
        return commands

App.all = [App(
    name=app['name'],
    app_dir=app['app-dir'],
    var_dir=app['var-dir'],
    log_dir=app['log-dir'],
    mount_dir=app['mount-dir'],
    mounts=[Mount(
        name=mount['name'],
        src=mount['src'],
        dst=mount['dst'],
    ) for mount in app['mounts']],
    copied=[CopyFile(
        app_dir=app['app-dir'],
        name=copied['name'],
        src=copied['src'],
        templated='templated' in copied and bool(copied['templated']),
    ) for copied in app['copied']],
) for app in CONFIG['apps']]

CopyFile.all = [cf for app in App.all for cf in app.copied]

def create_copy_commands() -> list[str]:
    return _flatten([app.create_copy_commands() for app in App.all])

def get_dirs() -> list[str]:
    dirs = [app.app_dir for app in App.all]
    dirs.extend([app.var_dir for app in App.all])
    dirs.extend([app.log_dir for app in App.all])
    dirs.extend([app.mount_dir for app in App.all])
    dirs.extend([mount.dst for mount in Mount.all])
    return dirs

def create_mkdir_command() -> str:
    return 'RUN ' + ' \\\n    && '.join(['mkdir -p {}'.format(dir) for dir in get_dirs()])

def create_apt_command() -> str:
    return ('RUN apt update && apt install -y '
        + ' \\\n    '.join(CONFIG['apt-packages']))

def create_pip3_command() -> str:
    return ('RUN pip3 install '
        + ' \\\n    '.join(CONFIG['pip3-packages']))

def create_dockerfile() -> str:
    df = eval_template(CONFIG['pre-setup'])
    df += create_apt_command() + '\n'
    df += create_pip3_command() + '\n'
    df += create_mkdir_command() + '\n'
    for cmd in create_copy_commands():
        df += cmd + '\n'
    df += eval_template(CONFIG['post-setup'])
    return df

def create_attach_command() -> str:
    return 'sudo podman exec --interactive --tty {} bash'.format(CONFIG['container-name'])

def create_podman_stop_command() -> str:
    return 'sudo podman stop {}'.format(CONFIG['container-name'])

def create_podman_rm_command() -> str:
    return 'sudo podman rm {}'.format(CONFIG['container-name'])

def create_podman_build_command() -> str:
    return 'sudo podman build -t {} .'.format(CONFIG['image-name'])

def create_podman_run_command(detach: bool, shell: bool) -> str:
    publish = ' '.join([
        '--publish {}:{}'.format(port, port)
        for port
        in CONFIG['ports']
    ])

    mount = ' '.join([
        '--mount type=bind,src={},dst={}'.format(mount.src, mount.dst)
        for mount in Mount.all
    ])

    return ' '.join([
        'sudo podman run',
        publish,
        mount,
        '--detach' if detach else '--rm --interactive --tty',
        '--hostname', CONFIG['hostname'],
        '--name', CONFIG['container-name'],
        CONFIG['image-name'],
        'bash' if shell else '',
    ])

# shortcuts
def file(name: str) -> pathlib.PurePath:
    return CopyFile.get(name).dst
def mount(name: str) -> pathlib.PurePath:
    return Mount.get(name).dst
def app_dir(name: str) -> pathlib.PurePath:
    return App.get(name).app_dir
def log_dir(name: str) -> pathlib.PurePath:
    return App.get(name).log_dir
def log_file(name: str) -> pathlib.PurePath:
    return App.get(name).log_dir / (name + '.log')
def var_dir(name: str) -> pathlib.PurePath:
    return App.get(name).var_dir
