# NoJava-IPMI-KVM

## Version incompatibility notice (upgrading from v0.8.1)

Users upgrading from version `v0.8.1` or earlier must rewrite their config files. The previously used ini format was not
flexible enough for adding HTML5 KVM support and was replaced with a [YAML](https://en.wikipedia.org/wiki/YAML) file.

Use the converter script
[`convert_config_file.py`](https://github.com/sciapp/nojava-ipmi-kvm/blob/master/convert_config_file.py)
to convert your old ini config file to the new YAML format.

## Introduction

`nojava-ipmi-kvm` is a tool for running Java-based IPMI-KVM consoles without a local Java installation. It runs a Docker
container in the background, starts a suitable Java Webstart version (from OpenJDK or Oracle) and connects to the
container with [noVNC](https://github.com/novnc/noVNC). By using Docker, Java Webstart is sandboxed automatically and
you don't need to install old Java versions on your Desktop machines.

Starting with version `v0.9.0`, `nojava-ipmi-kvm` also supports HTML5 based kvm viewers.

This project is based on ideas from [solarkennedy/ipmi-kvm-docker](https://github.com/solarkennedy/ipmi-kvm-docker).

## Deploying as a web service

If you would like to access IPMI-KVM consoles with a browser only (without Java plugins and a local installation of
`nojava-impi-kvm`), see [`nojava-ipmi-kvm-server`](https://github.com/sciapp/nojava-ipmi-kvm-server) which encapsulates
`nojava-ipmi-kvm` in a web service.

## Local Installation

The latest version can be obtained from PyPI and runs with Python 3.5+:

```bash
python3 -m pip install nojava-ipmi-kvm
```

[Install Docker](https://www.docker.com/) on your local machine if not done already (or Podman with Docker emulation).

If you run an Arch-based system, you can also install `nojava-ipmi-kvm` from the [AUR](https://aur.archlinux.org/):

```bash
yay -S nojava-ipmi-kvm-docker
```

If you prefer Podman to Docker use the Podman version instead:

```bash
yay -S nojava-ipmi-kvm-podman
```

## Usage

### Configuration file

First, create a file `~/.nojava-ipmi-kvmrc.yaml` and add a template for each kvm host type you want to connect to, for
example:

```yaml
templates:
  kvm-openjdk-7u51:
    skip_login: False
    login_user: ADMIN
    login_endpoint: rpc/WEBSES/create.asp
    allow_insecure_ssl: False
    user_login_attribute_name: WEBVAR_USERNAME
    password_login_attribute_name: WEBVAR_PASSWORD
    send_post_data_as_json: False
    session_cookie_key: SessionCookie
    download_endpoint: Java/jviewer.jnlp
    java_version: 7u51
    format_jnlp: False
```

-   `skip_login`: Skip the login to the KVM host (should be `False` in most cases). If the login is skipped, you can
    omit `login_user`, `login_endpoint`, `user_login_attribute_name` and `password_login_attribute_name`.
-   `login_user`: User to login to the web admin view (default: `ADMIN`)
-   `login_endpoint`: Relative POST url of the login form. Is needed to create a login session.
-   `allow_insecure_ssl`: Allow SSL certificates that cannot be validated when logging in and downloading the KVM
    viewer.
-   `user_login_attribute_name`: Name of the user login field in the login form (use the web inspector of your favorite
    browser to find out the field names).
-   `password_login_attribute_name`: Name of the password field in the login form.
-   `send_post_data_as_json`: Send the login POST request with JSON data as data payload (not needed in most cases)
-   `extra_login_form_fields`: Comma-separated list of key/value pairs which will be sent as additional data on the
    login request. Key and value must be separated by colon (example: `method:login`).
-   `session_cookie_key`: Workaround for web applications that do not set session cookies directly (for example with
    Javascript). If a login attempt does not set a session cookie, the HTTP reply body is scanned for a potential
    session cookie value. If a value is found, it will be stored under the name `session_cookie_key`. In most cases you
    can simply obmit this configuration key. This config value must also be set if `format_jnlp` is set to true.

-   Java-specific configuration keys:
    -   `download_endpoint`: Relative download url of the Java KVM viewer.
    -   `java_version`: Java version that is needed to run Java KVM viewer. Currently, `7u51`, `7u79`, `7u181`, `8u91`,
        `8u242`, `7u80-oracle` and `8u251-oracle` are available (default: `7u181`). The `-oracle` versions are special
        cases which require to build a Docker image yourself because of license restrictions. See [Using Oracle
        Java](#using-oracle-java) for more details.
    -   `format_jnlp`: Replace "{base_url}" and "{session_key}" in the jnlp file (not needed in most cases)
-   HTML5-specific configuration keys:
    -   `html5_endpoint`: Relative url of the HTML5 kvm console.
    -   `rewrites`: List of transformations / patches which must be applied to the HTML5 kvm console code for embedding
        into another web root. Every transformation is described by a dictionary containing the keys `search` (regular
        expression), `replace` and `path_match` (regular expression which specifies which urls will be patched). The
        placeholder `{subdirectory}` contains the new root path.

        Example:

        ```yaml
        rewrites:
        - search: 'var path=""'
          replace: 'var path="{subdirectory}"'
          path_match: "/novnc/include/nav_ui\\.js$"
        ```

Then, add a definition for every single kvm host by reusing the previously defined templates:

```yaml
hosts:
  mykvmhost:
    based_on: kvm-openjdk-7u51
    full_hostname: mykvmhost.org
```

-   `based_on`: Template to use for this host configuration
-   `full_hostname`: Fully qualified name of your KVM host

Template configuration values can be overwritten in the host section.

In addition, you can create a `general` section to configure more general settings, e.g.:

```
general:
  run_docker_with_sudo: False
  x_resolution: 1600x1200
```

-   `run_docker_with_sudo`: Set to True if the `docker` command must be called with `sudo` (needed on Linux if your user
    account is not a member of the `docker` group, defaults to `False`).
-   `x_resolution`: Resolution of the X server and size of the VNC window (default: `1024x768`).
-   `java_docker_image`: Docker image for Java-based kvm consoles (default:
    `sciapp/nojava-ipmi-kvm:v{version}-{java_provider}-{java_major_version}`).
-   `html5_docker_image`: Docker image for Java-based kvm consoles (default: `sciapp/nojava-ipmi-kvm:v{version}-html5`).

Unless you want to use custom docker images, you can omit the config keys `java_docker_image` and `html5_docker_image`.

### Using the command line tool

After configuring, you can call `nojava-ipmi-kvm` from the command line:

```bash
nojava-ipmi-kvm mykvmhost
```

You can start `nojava-ipmi-kvm` multiple times to connect to different machines in parallel. The background Docker
container will be shutdown automatically after to you closed the VNC window (if invoked with the `--use-gui` flag) or
sent `<Ctrl-C>` on the command line.

Options:

```
usage: nojava-ipmi-kvm [-h] [--debug] [-f CONFIG_FILEPATH] [-g]
                       [--print-default-config] [-V]
                       [hostname]

nojava-ipmi-kvm is a utility to access Java based ipmi kvm consoles without a local java installation.

positional arguments:
  hostname              short hostname of the server machine; must be
                        identical with a hostname in `.nojava-ipmi-kvmrc` (for
                        example `mykvmserver`)

optional arguments:
  -h, --help            show this help message and exit
  --debug               print debug messages
  -f CONFIG_FILEPATH, --config-file CONFIG_FILEPATH
                        login user (default: ~/.nojava-ipmi-kvmrc)
  -g, --use-gui         automatically open a PyQt5 browser window. Requires
                        PyQt5 to be installed
  --print-default-config
                        print the default config to stdout and exit
  -V, --version         print the version number and exit
```

## Using Oracle Java

Because of license restrictions we cannot provide pre-built docker images for Oracle Java. However, you can build an
Oracle Java image yourself:

1. Clone this repository:

   ```bash
   git clone git@github.com:sciapp/nojava-ipmi-kvm.git
   ```

2. Visit [the Java download page](https://www.java.com/en/download/manual.jsp) and get the *Linux x64* tar archive of
   Oracle Java version `8u251`. Save it to the `docker` subdirectory of the previously cloned repository as
   `jre-8u251-linux-x64.tar.gz`. If you would like to also use Oracle Java 7, get `jre-7u80-linux-x64.tar.gz` from
   [Oracle's Java archive](https://www.oracle.com/java/technologies/javase/javase7-archive-downloads.html) (this
   requires an free Oracle account).

3. Open a terminal and go to the root of the project clone. Run

   ```bash
   git pull
   make build-oracle
   ```

   to build a Docker image with Oracle Java. When you install an updated version of `nojava-ipmi-kvm` repeat these
   commands.

4. Use `java_version: 8u251-oracle` (or `7u80-oracle`) in your `~/.nojava-ipmi-kvmrc.yaml` configuration.

## Command line completion

This repository offers a completion script for bash and zsh (only hostnames currently, no options).

### Bash

Download [the Bash completion
file](https://raw.githubusercontent.com/sciapp/nojava-ipmi-kvm/master/completion/bash/nojava-ipmi-kvm-completion.bash)
and source it in your `.bashrc`, for example by running:

```bash
curl -o .nojava-ipmi-kvm-completion.bash -L https://raw.githubusercontent.com/sciapp/nojava-ipmi-kvm/master/completion/bash/nojava-ipmi-kvm-completion.bash
echo '[ -r "${HOME}/.nojava-ipmi-kvm-completion.bash" ] && source "${HOME}/.nojava-ipmi-kvm-completion.bash"' >> ~/.bashrc
```

### Zsh

You can install the completion script with [zplug](https://github.com/zplug/zplug) or manually.

#### Using zplug

Add `zplug "sciapp/nojava-ipmi-kvm"` to your `.zshrc`, open a new shell and run

```bash
zplug install
```

#### Manual

Clone this repository and source `nojava_ipmi_kvm_completion.plugin.zsh` in your `.zshrc`.

## Acknowledgement

-   Special thanks to @mheuwes for adding the new YAML config file format and adding HTML5 support!
