# NoJava-IPMI-KVM

## Introduction

*NoJava-IPMI-KVM* is a tool for running Java-based IPMI-KVM consoles without a local Java installation. It runs a Docker
container in the background, starts a suitable Java Webstart version (from OpenJDK) and connects to the container with
[noVNC](https://github.com/novnc/noVNC). By using Docker, Java Webstart is sandboxed automatically and you don't need to
install old Java versions on your Desktop machines.

This project is based on ideas from [solarkennedy/ipmi-kvm-docker](https://github.com/solarkennedy/ipmi-kvm-docker).

## Installation

The latest version can be obtained from PyPI and runs with Python 2.7 or 3.3+ (Python 3 is recommended):

```bash
python3 -m pip install nojava-ipmi-kvm
```

[Install Docker](https://www.docker.com/) on your local machine if not done already.

## Usage

### Configuration file

First, create a file `~/.nojava-ipmi-kvmrc` and create a configuration section for each kvm host you want to connect to,
for example:

```
[myhostkvm]
full_hostname = myhostkvm.org
login_user = ADMIN
login_endpoint = rpc/WEBSES/create.asp
download_endpoint = Java/jviewer.jnlp
allow_insecure_ssl = False
user_login_attribute_name = WEBVAR_USERNAME
password_login_attribute_name = WEBVAR_PASSWORD
java_version = 7u51
session_cookie_key = SessionCookie
```

-   `full_hostname`: Fully qualified name of your KVM host
-   `login_user`: User to login to the web admin view (default: `ADMIN`)
-   `login_endpoint`: Relative POST url of the login form. Is needed to create a login session.
-   `download_endpoint`: Relative download url of the Java KVM viewer.
-   `allow_insecure_ssl`: Allow SSL certificates that cannot be validated when logging in and downloading the KVM
    viewer.
-   `user_login_attribute_name`: Name of the user login field in the login form (use the web inspector of your favorite
    browser to find out the field names).
-   `password_login_attribute_name`: Name of the password field in the login form.
-   `java_version`: Java version that is needed to run Java KVM viewer. Currently, `7u51` and `7u181` are available
    (default: `7u181`).
-   `session_cookie_key`: Workaround for web applications that do not set session cookies directly (for example with
    Javascript). If a login attempt does not set a session cookie, the HTTP reply body is scanned for a potential
    session cookie value. If a value is found, it will be stored under the name `session_cookie_key`. In most cases you
    can simply obmit this configuration key.


In addition, you can create a `general` section to configure more general settings, e.g.:

```
[general]
run_docker_with_sudo = False
x_resolution = 1600x1200
```

-   `run_docker_with_sudo`: Set to True if the `docker` command must be called with `sudo` (needed on Linux if your user
    account is not a member of the `docker` group, defaults to `False`)
-   `x_resolution`: Resolution of the X server and size of the VNC window (default: `1024x768`)

### Using the command line tool

After configuring, you can call `nojava-ipmi-kvm` from the command line:

```bash
nojava-ipmi-kvm myhostkvm
```

You can start `nojava-ipmi-kvm` multiple times to connect to different machines in parallel. The background Docker
container will be shutdown automatically after to you closed the VNC window or sent `<Ctrl-C>` on the command line.

Options:

```
usage: nojava-ipmi-kvm [-h] [-f CONFIG_FILEPATH] [--print-default-config] [-V]
                       [hostname]

nojava-ipmi-kvm is a utility to access Java based ipmi kvm consoles without a local java installation.

positional arguments:
  hostname              short hostname of the server machine; must be
                        identical with a hostname in `.nojava-ipmi-kvmrc` (for
                        example `mykvmserver`)

optional arguments:
  -h, --help            show this help message and exit
  -f CONFIG_FILEPATH, --config-file CONFIG_FILEPATH
                        login user (default: ~/.nojava-ipmi-kvmrc)
  --print-default-config
                        print the default config to stdout and exit
  -V, --version         print the version number and exit
```

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
