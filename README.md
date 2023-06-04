
# server

my server. slightly cursed.

## prerequisites

- domain names of course.
- ansible
  - probably also the `acl` package
- probably should just read the playbooks and config files to make sure it
  will all work on your system

```bash
cd deploy
ansible-playbook nginx.yml
ansible-playbook syncthing.yml
ansible-playbook shrub-bot.yml
ansible-playbook spotti.yml
ansible-playbook pages.yml
ansible-playbook cabbage-size.yml
ansible-playbook dart-or-penny.yml
```

## caveats

- the htpasswd file for dart-or-penny is a little fucky. it needs to be staged
  manually in the nginx.dir directory. see deploy/nginx.yml
- the certs are also a little fucky. certbot is annoying in that it persists
  some data when you create certs.
- the dop user needs read permissions in the syncthing.data_dir and write perms
  in syncthing.data_dir/thumbnails

## todo

- a lot of the stuff in the config files could still be templated out
- ssl cert renewal
- syncthing configs (how?)
