-- vim: ft=dhall et ts=2 sw=2

let List/map =
  https://prelude.dhall-lang.org/v11.1.0/List/map sha256:dd845ffb4568d40327f2a817eb42d1c6138b929ca758d50bc33112ef3c885680

let base-dir = "/app"
let withBaseDir = \(dir: Text) ->
  "${base-dir}/${dir}"

let Mount = {
  name: Text, -- path relative to App.mount-dir
  src: Text,  -- path on host system
  dst: Text,  -- absolute path in container
}

let CopyFile = {
  name: Text, -- just a name
  src: Text,  -- path on host system, basename to be extracted
  templated: Optional Bool
}

let App = {
  name: Text,
  app-dir: Text,
  var-dir: Text,
  log-dir: Text,
  mount-dir: Text,
  mounts: List Mount,
  copied: List CopyFile,
}

let makeApp: Text -> List CopyFile -> App =
  \(name: Text) ->
  \(copied: List CopyFile) ->
  let app-dir = withBaseDir name
  let editCopied = List/map CopyFile CopyFile (
    \(file: CopyFile) -> file // {
      name = name ++ "-" ++ file.name,
    })
  in {
    name,
    app-dir,
    var-dir = app-dir ++ "/var",
    log-dir = app-dir ++ "/log",
    mount-dir = app-dir ++ "/mnt",
    mounts = ([]: List Mount),
    copied = editCopied copied,
  }

let NotMount = { src: Text, name: Text }
let withMounts: App -> List NotMount -> App =
  \(app: App) ->
  \(mounts: List NotMount) ->
  let toMounts = List/map NotMount Mount (
    \(notMount: NotMount) -> {
      name = app.name ++ "-" ++ notMount.name,
      src = notMount.src,
      dst = app.mount-dir ++ "/" ++ notMount.name,
    }
  ) in app // {
    mounts = app.mounts # toMounts mounts,
  }

let noCopyFiles = ([]: List CopyFile)
let normal = \(rec: { name: Text, src: Text }) ->
  rec // { templated = None Bool }
let templated = \(rec: { name: Text, src: Text }) ->
  rec // { templated = Some True }

let supervisord = makeApp "supervisord" [
  templated { name = "config", src = "supervisord.conf" },
]

let not-cron = makeApp "not-cron" [
  normal { name = "binary", src = "not-cron/target/release/not-cron" },
  templated { name = "not-crontab", src = "not-cron.toml" },
]

let cabbage-size = makeApp "cabbage-size" [
  normal { name = "binary", src = "cabbage-size/target/release/cs" },
  templated { name = "config", src = "cabbage-size.toml" },
  templated { name = "rocket", src = "cabbage-size-rocket.toml" },
]

let shrub_bot = makeApp "shrub_bot" [
  normal { name = "source", src = "shrub_bot/shrub_bot.py" },
  templated { name = "config", src = "shrub-bot.toml" },
]

let spotti-downbot = makeApp "spotti-downbot" [
  normal { name = "source", src = "spotti/bot/downbot.py" },
  templated { name = "config", src = "spotti-downbot.toml" },
  templated { name = "cron", src = "spotti/scripts/cron.sh" },
]

let spotti = withMounts (makeApp "spotti" [
  normal { name = "binary", src = "spotti/target/release/spotti" },
  templated { name = "config", src = "spotti.toml" },
]) [
  { name = "database", src = "mounts/spotti" },
]

let nginx = withMounts (makeApp "nginx" [
  normal { name = "www", src = "www" },
  templated { name = "sites", src = "sites.conf" },
  templated { name = "config", src = "nginx.conf" },
]) [
  { name = "certs", src = "mounts/certs" },
]

let syncthing = withMounts (makeApp "syncthing" noCopyFiles) [
  { name = "data", src = "/mnt/syncthing" },
  { name = "conf", src = "mounts/syncthing/conf" },
]

let dart-or-penny = withMounts (makeApp "dart-or-penny" [
  normal { name = "binary", src = "dart-or-penny/target/release/dart-or-penny" },
  templated { name = "config", src = "dart-or-penny.toml" },
]) [
  { name = "thumbnails", src = "/mnt/syncthing/thumbnails" },
]

in {
  hostname = "herber-t",
  container-name = "the-server",
  image-name = "server",
  ports = [443, 80],

  apps = [
    supervisord,
    not-cron,
    cabbage-size,
    shrub_bot,
    spotti-downbot,
    spotti,
    nginx,
    syncthing,
    dart-or-penny,
  ],

  apt-packages = [
    "python3-pip",
    "nginx",
    "supervisor",
    "pkg-config",
    "curl",
    "syncthing",
  ],

  pip3-packages = [
    "discord.py==2.1.0",
    "toml==0.10.2",
    "requests==2.25.1",
  ],

  pre-setup = ''
FROM docker.io/ubuntu:jammy
COPY sources.list /etc/apt/
'',

  post-setup = ''
EXPOSE 80
CMD supervisord -c {{ file('supervisord-config') }}
'',
}
