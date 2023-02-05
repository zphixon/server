#!/bin/env python3

import subprocess
import sys
import argparse
import os
import operator
import functools
import gen_config

class DuckCompletedProcess:
    def __init__(self):
        self.returncode = 0
        self.stdout = ''

class Command:
    actually = True
    def run(command: str, capture=False, env={}, shell=False):
        command_stripped = command.strip()
        print('>>>>>', command_stripped)
        command_args = command_stripped.split(' ')
        if not Command.actually:
            return DuckCompletedProcess()
        stdout = None
        if capture:
            stdout = subprocess.PIPE
        if shell:
            command_args = ' '.join(command_args)
        return subprocess.run(
            command_args,
            stdout=stdout,
            env=os.environ|env,
            shell=shell
        )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--update', action='store_true', help='update git repo and submodules')
    parser.add_argument('--build', action='store_true', help='build image')
    parser.add_argument('--clean', action='store_true', help='clean images')
    parser.add_argument('--shell', action='store_true', help='run with shell')
    parser.add_argument('--detach', action='store_true', help='detach after starting')
    parser.add_argument('--attach', action='store_true', help='attach to running container')
    parser.add_argument('--dry-run', action='store_true', help='only print commands to be run')
    args = parser.parse_args()

    if not functools.reduce(operator.or_, [
        args.update,
        args.build,
        args.clean,
        args.shell,
        args.detach,
        args.attach,
    ]):
        print('need an action')
        parser.print_help()
        sys.exit(1)

    if args.shell and args.detach:
        print('--shell incompatible with --detach')
        sys.exit(1)

    if args.shell and args.attach:
        print('--shell incompatible with --attach')
        sys.exit(1)

    if args.dry_run:
        Command.actually = False

    if args.attach:
        Command.run(gen_config.create_attach_command())
        sys.exit(0)

    if args.build or args.detach or args.shell or args.clean:
        Command.run(gen_config.create_podman_stop_command())
        Command.run(gen_config.create_podman_rm_command())

    if args.clean:
        Command.run('sudo podman rmi -f `sudo podman images -qa`', shell=True)

    if args.update:
        if Command.run('git pull').returncode != 0 or Command.run('git submodule update --init').returncode != 0:
            print('git broke')
            sys.exit(1)

    if args.build:
        for app in gen_config.App.all:
            for file in app.get_templated():
                print('>>>>>', 'update config file', file.template_src)
                if Command.actually:
                    file.do_template()

        new_df = gen_config.create_dockerfile()
        print('>>>>>', 'overwrite Dockerfile')
        print(new_df)
        if Command.actually:
            df = open('Dockerfile', 'w+')
            df.write(new_df)
            df.close()

        cwd = os.getcwd()
        os.chdir('spotti')
        if Command.run(
            'cargo b --release',
            env={'DATABASE_URL': 'sqlite:///home/zack/spotti/recents.db'}
        ).returncode != 0:
            print('build spotti broke')
            os.chdir(cwd)
            sys.exit(1)

        os.chdir(cwd)
        os.chdir('cabbage-size')
        if Command.run('cargo b --release').returncode != 0:
            print('build cabbagesize broke')
            os.chdir(cwd)
            sys.exit(1)
        os.chdir(cwd)

        os.chdir(cwd)
        os.chdir('not-cron')
        if Command.run('cargo b --release').returncode != 0:
            print('build not-cron broke')
            os.chdir(cwd)
            sys.exit(1)
        os.chdir(cwd)

        if Command.run(gen_config.create_podman_build_command()).returncode != 0:
            print('build container broke')
            sys.exit(1)

    if args.detach or args.shell:
        command = gen_config.create_podman_run_command(
            shell=args.shell, detach=args.detach
        )
        Command.run(command)

