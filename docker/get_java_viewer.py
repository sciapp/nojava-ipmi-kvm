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
import getpass
import os
import re
import requests
import urllib.parse
import sys

try:
    from typing import Any  # noqa: F401  # pylint: disable=unused-import
except ImportError:
    pass


__author__ = "Ingo Heimbach"
__email__ = "i.heimbach@fz-juelich.de"
__copyright__ = "Copyright © 2018 Forschungszentrum Jülich GmbH. All rights reserved."
__license__ = "MIT"
__version_info__ = (0, 0, 0)
__version__ = ".".join(map(str, __version_info__))


DEFAULT_DO_SSL_VERIFY = True
DEFAULT_DOWNLOAD_ENDPOINT = "cgi/url_redirect.cgi?url_name=ikvm&url_type=jwsk"
DEFAULT_LOGIN_ENDPOINT = "cgi/login.cgi"
DEFAULT_USER = "ADMIN"

DEFAULTS = {
    "attribute_names": {"user": "name", "password": "pwd"},
    "do_ssl_verify": True,
    "download_location": "kvm_console.jnlp",
    "endpoints": {"download": "cgi/url_redirect.cgi?url_name=ikvm&url_type=jwsk", "login": "cgi/login.cgi"},
    "login_user": "ADMIN",
}


class InvalidHostnameError(Exception):
    pass


class LoginFailedError(Exception):
    pass


class DownloadFailedError(Exception):
    pass


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
%(prog)s is a utility for downloading kvm console applications from webpages secured with logins.
""",
    )
    parser.add_argument(
        "hostname", action="store", help="hostname of the server machine (for example `mykvmserver.com`)"
    )
    parser.add_argument(
        "-u",
        "--user",
        action="store",
        dest="user",
        default=DEFAULTS["login_user"],
        help="login user (default: %(default)s)",
    )
    parser.add_argument(
        "-o",
        "--download-location",
        action="store",
        dest="download_location",
        default=DEFAULTS["download_location"],
        help="download path of the kvm viewer file (default: %(default)s)",
    )
    parser.add_argument(
        "-l",
        "--login-endpoint",
        action="store",
        dest="login_endpoint",
        default=DEFAULTS["endpoints"]["login"],
        help="login url endpoint (default: %(default)s)",
    )
    parser.add_argument(
        "-k",
        "--insecure",
        action="store_false",
        dest="ssl_verify",
        default=DEFAULTS["do_ssl_verify"],
        help="allow insecure SSL connections (-> SSL without certificate verification) (default: %(default)s)",
    )
    parser.add_argument(
        "-d",
        "--download-endpoint",
        action="store",
        dest="download_endpoint",
        default=DEFAULTS["endpoints"]["download"],
        help="download url endpoint (default: %(default)s)",
    )
    parser.add_argument(
        "-U",
        "--user-attribute",
        action="store",
        dest="user_attribute_name",
        default=DEFAULTS["attribute_names"]["user"],
        help="name of the user form field on the login page (default: %(default)s)",
    )
    parser.add_argument(
        "-P",
        "--password-attribute",
        action="store",
        dest="password_attribute_name",
        default=DEFAULTS["attribute_names"]["password"],
        help="name of the password form field on the login page (default: %(default)s)",
    )
    parser.add_argument(
        "-V", "--version", action="store_true", dest="print_version", help="print the version number and exit"
    )
    return parser


def parse_arguments():
    # type: () -> AttributeDict
    parser = get_argumentparser()
    args = AttributeDict({key: value for key, value in vars(parser.parse_args()).items()})
    if not args.print_version:
        match_obj = re.match(r"(?:https?//)?(.+)/?", args.hostname)
        if match_obj:
            args.hostname = match_obj.group(1)
        else:
            raise InvalidHostnameError("{} is not a valid server name.".format(args.hostname))
        if sys.stdin.isatty():
            args.password = getpass.getpass()
        else:
            args.password = sys.stdin.readline().rstrip()
    return args


def get_java_viewer(
    hostname,
    user,
    password,
    download_location,
    login_endpoint,
    download_endpoint,
    ssl_verify,
    user_attribute_name,
    password_attribute_name,
):
    # type: (str, str, str, str, str, str, bool, str, str) -> None
    base_url = "https://{}".format(hostname)
    download_url = urllib.parse.urljoin(base_url, download_endpoint)
    login_url = urllib.parse.urljoin(base_url, login_endpoint)

    session = requests.Session()
    # Login to get a session cookie
    response = session.post(
        login_url, verify=ssl_verify, data={user_attribute_name: user, password_attribute_name: password}
    )
    if response.status_code != 200 or not session.cookies:
        raise LoginFailedError("Login to {} was not successful".format(login_url))
    # Download the kvm viewer with the previous created session
    response = session.get(download_url)
    if response.status_code != 200:
        raise DownloadFailedError("Downloading the ipmi kvm viewer file from {} failed".format(download_url))
    with open(download_location, "w", encoding="utf-8") as f:
        f.write(response.text)


def main():
    # type: () -> None
    args = parse_arguments()
    if args.print_version:
        print("{}, version {}".format(os.path.basename(sys.argv[0]), __version__))
    else:
        get_java_viewer_exceptions = (LoginFailedError, DownloadFailedError, IOError)
        try:
            get_java_viewer(
                args.hostname,
                args.user,
                args.password,
                args.download_location,
                args.login_endpoint,
                args.download_endpoint,
                args.ssl_verify,
                args.user_attribute_name,
                args.password_attribute_name,
            )
        except get_java_viewer_exceptions as e:
            print(str(e), file=sys.stderr)
            for i, exception_class in enumerate(get_java_viewer_exceptions, start=3):
                if isinstance(i, exception_class):
                    sys.exit(i)
            sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
