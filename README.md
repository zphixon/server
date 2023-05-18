
# server

my server. slightly cursed.

## prerequisites

- domain names of course.
- docker/podman. I like podman, idk why. it should work with either. you'll
  have to edit the deploy script though
- mount points for the spotti db, letsencrypt ssl certs, and syncthing stuff

```bash
./deploy --build   # build the container and image
./deploy --detach  # run it detached
```

## caveats

in particular the certs are a little fucky. theoretically it should be as
simple as just running certbot renew outside the container and having it work
but who knows. we'll cross that bridge when we get to it.

it needs all these files in the same mount point.

- /etc/letsencrypt/live/allOfEm/*
- /etc/letsencrypt/ssl-dhparams.conf
- /etc/letsencrypt/options-ssl-nginx.conf

also, the db is a little fucky too. it needs to exist at compile time *and* at
runtime but in different locations. see the DATABASE_URL env var in the deploy
script vs the db_file key in spotti.toml to to see what I mean.

generate new certs with:

```bash
certbot certonly --cert-name allOfEm -d gang-and-friends.com -d grape.surgery -d oatmeal.gay
```

and copy 'em to the mount point?
