#!/usr/bin/env python3

import argparse
import getpass
import logging
import os
import signal
import sys
import asyncio

try:
    from typing import Any  # noqa: F401  # pylint: disable=unused-import
except ImportError:
    pass
from .config import config, DEFAULT_CONFIG_FILEPATH, InvalidHostnameError
from .kvm import (
    start_kvm_container,
    WebserverNotReachableError,
    DockerNotInstalledError,
    DockerNotCallableError,
    DockerTerminatedError,
)
from . import browser
from ._version import __version__, __version_info__  # noqa: F401  # pylint: disable=unused-import

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
if sys.stderr.isatty():
    logging.addLevelName(logging.ERROR, "\033[1;31m%s\033[1;0m" % logging.getLevelName(logging.ERROR))


def get_argumentparser():
    # type: () -> argparse.ArgumentParser
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
%(prog)s is a utility to access Java based ipmi kvm consoles without a local java installation.""",
    )
    parser.add_argument(
        "hostname",
        action="store",
        nargs="?",
        help="short hostname of the server machine; must be identical with a hostname in `.nojava-ipmi-kvmrc` "
        "(for example `mykvmserver`)",
    )
    parser.add_argument(
        "-f",
        "--config-file",
        action="store",
        dest="config_filepath",
        default=DEFAULT_CONFIG_FILEPATH,
        help="login user (default: %(default)s)",
    )
    parser.add_argument(
        "--print-default-config",
        action="store_true",
        dest="print_default_config",
        help="print the default config to stdout and exit",
    )
    parser.add_argument(
        "--use-gui",
        action="store_true",
        dest="use_gui",
        help="automatically open a PyQt5 browser window. Requires PyQt5 to be installed"
    )
    parser.add_argument(
        "-V", "--version", action="store_true", dest="print_version", help="print the version number and exit"
    )
    return parser


def parse_arguments():
    # type: () -> AttributeDict
    parser = get_argumentparser()
    args = parser.parse_args()
    if not args.print_version and not args.print_default_config:
        if args.hostname is None:
            parser.print_help()
            sys.exit(0)
        args.config_filepath = args.config_filepath
    return args


def read_password():
    # type: () -> Text
    if sys.stdin.isatty():
        password = getpass.getpass()
    else:
        password = sys.stdin.readline().rstrip()
    return password


def setup_signal_handling():
    # type: () -> None
    # Handle SIGINT like SIGTERM
    signal.signal(signal.SIGINT, lambda sig, frame: os.kill(os.getpid(), signal.SIGTERM))
    # Do a normal program exit on SIGTERM to ensure all exit handlers will be run (-> `atexit`)
    signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))


def main():
    # type: () -> None
    args = parse_arguments()
    if args.print_version:
        print("{}, version {}".format(os.path.basename(sys.argv[0]), __version__))
    elif args.print_default_config:
        config.write_default_config(sys.stdout)
        sys.exit(0)
    else:
        setup_signal_handling()
        start_kvm_container_exceptions = (
            InvalidHostnameError,
            WebserverNotReachableError,
            DockerNotInstalledError,
            DockerNotCallableError,
            DockerTerminatedError,
        )
        try:
            config.read_config(args.config_filepath)
            host_config = config[args.hostname]
            password = read_password()
            kvm_viewer = asyncio.get_event_loop().run_until_complete(start_kvm_container(
                host_config.full_hostname,
                host_config.login_user,
                password,
                host_config.login_endpoint,
                host_config.download_endpoint,
                host_config.allow_insecure_ssl,
                host_config.user_login_attribute_name,
                host_config.password_login_attribute_name,
                host_config.java_version,
                host_config.session_cookie_key,
            ))
            if args.use_gui and browser.qt_installed:
                browser.run_vnc_browser(
                    kvm_viewer.url,
                    host_config.full_hostname,
                    tuple(int(c) for c in config.x_resolution.split("x")),
                )
            else:
                print("Use this url: %s to view kvm." % kvm_viewer.url)
                print("Press ENTER or CTRL-C to shutdown container and exit")
                sys.stdin.readline()
            kvm_viewer.kill_process()
        except start_kvm_container_exceptions as e:
            logging.error(str(e))
            for i, exception_class in enumerate(start_kvm_container_exceptions, start=3):
                if isinstance(e, exception_class):
                    sys.exit(i)
            sys.exit(1)
        except KeyboardInterrupt:
            pass
    sys.exit(0)


if __name__ == "__main__":
    main()
