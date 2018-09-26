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
import re
import requests
import urllib.parse
import sys

try:
    from typing import Any, Optional, Text  # noqa: F401  # pylint: disable=unused-import
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
if sys.stderr.isatty():
    logging.addLevelName(logging.INFO, "\033[1;34m%s\033[1;0m" % logging.getLevelName(logging.INFO))
    logging.addLevelName(logging.ERROR, "\033[1;31m%s\033[1;0m" % logging.getLevelName(logging.ERROR))


PY2 = sys.version_info.major < 3  # is needed for correct mypy checking

if PY2:
    str = unicode  # use unicode instead of future `str` since requests cannot handle future `str` well
    stdin = codecs.getreader("utf-8")(sys.stdin)
else:
    basestring = str
    stdin = sys.stdin


__author__ = "Ingo Heimbach"
__email__ = "i.heimbach@fz-juelich.de"
__copyright__ = "Copyright © 2018 Forschungszentrum Jülich GmbH. All rights reserved."
__license__ = "MIT"
__version_info__ = (0, 1, 0)
__version__ = ".".join(map(str, __version_info__))


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
        # type: (Text) -> Any
        return self[attr]

    def __setattr__(self, attr, value):
        # type: (Text, Any) -> None
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
        "-d",
        "--download-endpoint",
        action="store",
        dest="download_endpoint",
        default=DEFAULTS["endpoints"]["download"],
        help="download url endpoint (default: %(default)s)",
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
        "-K", "--session-cookie-key", action="store", dest="session_cookie_key", help="name of the session cookie key"
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
    if not args.print_version:
        match_obj = re.match(r"(?:https?//)?(.+)/?", args.hostname)
        if match_obj:
            args.hostname = match_obj.group(1)
        else:
            raise InvalidHostnameError("{} is not a valid server name.".format(args.hostname))
    return args


def read_password():
    # type: () -> Text
    if sys.stdin.isatty():
        password = getpass.getpass()
    else:
        password = stdin.readline().rstrip()
    return password


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
    session_cookie_key=None,
):
    # type: (Text, Text, Text, Text, Text, Text, bool, Text, Text, Optional[Text]) -> None
    base_url = "https://{}".format(hostname)
    download_url = urllib.parse.urljoin(base_url, download_endpoint)
    login_url = urllib.parse.urljoin(base_url, login_endpoint)

    session = requests.Session()
    # Login to get a session cookie
    response = session.post(
        login_url, verify=ssl_verify, data={user_attribute_name: user, password_attribute_name: password}
    )
    if response.status_code == 200 and not any(
        re.search(r"(session)|(SESSION)", key) for key in session.cookies.keys()
    ):
        session_cookie_regex = re.compile(r"'?(\w*(?:session)|(?:SESSION)\w*)'?\s*[:=]\s*'(\w+)'")
        for line in response.text.split("\n"):
            match_obj = session_cookie_regex.search(line)
            if match_obj is not None:
                if session_cookie_key is None:
                    session_cookie_key = match_obj.group(1)
                session_cookie_value = match_obj.group(2)
                session.cookies.set(session_cookie_key, session_cookie_value)
                break
    if response.status_code != 200 or not session.cookies:
        raise LoginFailedError("Login to {} was not successful.".format(login_url))
    logging.info("Logged in to {} as {}".format(hostname, user))
    # Download the kvm viewer with the previous created session
    response = session.get(download_url)
    if response.status_code != 200:
        raise DownloadFailedError("Downloading the ipmi kvm viewer file from {} failed.".format(download_url))
    logging.info("Successfully downloaded the kvm viewer.")
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
            password = read_password()
            get_java_viewer(
                args.hostname,
                args.user,
                password,
                args.download_location,
                args.login_endpoint,
                args.download_endpoint,
                args.ssl_verify,
                args.user_attribute_name,
                args.password_attribute_name,
                args.session_cookie_key,
            )
        except get_java_viewer_exceptions as e:
            logging.error(str(e))
            for i, exception_class in enumerate(get_java_viewer_exceptions, start=3):
                if isinstance(e, exception_class):
                    sys.exit(i)
            sys.exit(1)
        except KeyboardInterrupt:
            pass
    sys.exit(0)


if __name__ == "__main__":
    main()
