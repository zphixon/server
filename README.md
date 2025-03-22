
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
ansible-playbook -e @secret.yml -i hosts.ini -k nginx.yml
ansible-playbook -e @secret.yml -i hosts.ini -k syncthing.yml
ansible-playbook -e @secret.yml -i hosts.ini -k shrub-bot.yml
ansible-playbook -e @secret.yml -i hosts.ini -k spotti.yml
ansible-playbook -e @secret.yml -i hosts.ini -k pages.yml
ansible-playbook -e @secret.yml -i hosts.ini -k dart-or-penny.yml
```

## caveats

- the certs are a little fucky. certbot is annoying in that it persists
  some data when you create certs.
- the dop user needs read permissions in the syncthing.data_dir and write perms
  in syncthing.data_dir/thumbnails

## todo

- a lot of the stuff in the config files could still be templated out
- syncthing configs (how?)
