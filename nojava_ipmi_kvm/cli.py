#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from builtins import *  # noqa: F401,F403  pylint: disable=redefined-builtin,wildcard-import,unused-wildcard-import
from future import standard_library

standard_library.install_aliases()  # noqa: E402

import argparse
import codecs
import getpass
import logging
import os
import sys

try:
    from typing import Any  # noqa: F401  # pylint: disable=unused-import
except ImportError:
    pass
from .config import config, DEFAULT_CONFIG_FILEPATH, InvalidHostnameError
from .kvm import (
    view_kvm_console,
    WebserverNotReachableError,
    DockerNotInstalledError,
    DockerNotCallableError,
    DockerTerminatedError,
)
from ._version import __version__, __version_info__  # noqa: F401  # pylint: disable=unused-import

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
if sys.stderr.isatty():
    logging.addLevelName(logging.ERROR, "\033[1;31m%s\033[1;0m" % logging.getLevelName(logging.ERROR))


PY2 = sys.version_info.major < 3  # is needed for correct mypy checking

if PY2:
    stdin = codecs.getreader("utf-8")(sys.stdin)
else:
    basestring = str
    stdin = sys.stdin


class AttributeDict(dict):
    def __getattr__(self, attr):
        # type: (str) -> Any
        return self[attr]

    def __setattr__(self, attr, value):
        # type: (str, Any) -> None
        self[attr] = value


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
        "-V", "--version", action="store_true", dest="print_version", help="print the version number and exit"
    )
    return parser


def parse_arguments():
    # type: () -> AttributeDict
    parser = get_argumentparser()
    args = AttributeDict(  # Ensure that all strings are unicode strings (relevant for Python 2 only)
        {
            str(key): str(value) if isinstance(value, basestring) else value
            for key, value in vars(parser.parse_args()).items()
        }
    )
    if not args.print_version and not args.print_default_config:
        if args.hostname is None:
            parser.print_help()
            sys.exit(0)
        args.config_filepath = os.path.abspath(os.path.expanduser(args.config_filepath))
    return args


def read_password():
    # type: () -> Text
    if sys.stdin.isatty():
        password = getpass.getpass()
    else:
        password = stdin.readline().rstrip()
    return password


def main():
    # type: () -> None
    args = parse_arguments()
    if args.print_version:
        print("{}, version {}".format(os.path.basename(sys.argv[0]), __version__))
    elif args.print_default_config:
        config.write_default_config(sys.stdout)
        sys.exit(0)
    else:
        view_kvm_console_exceptions = (
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
            view_kvm_console(
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
            )
        except view_kvm_console_exceptions as e:
            logging.error(str(e))
            for i, exception_class in enumerate(view_kvm_console_exceptions, start=3):
                if isinstance(e, exception_class):
                    sys.exit(i)
            sys.exit(1)
        except KeyboardInterrupt:
            pass
    sys.exit(0)


if __name__ == "__main__":
    main()
