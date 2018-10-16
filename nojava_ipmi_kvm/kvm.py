# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from builtins import *  # noqa: F401,F403  pylint: disable=redefined-builtin,wildcard-import,unused-wildcard-import
from future import standard_library

standard_library.install_aliases()  # noqa: E402

import logging
import os
import platform
import requests
import signal
import subprocess
import sys
import time
import uuid

try:
    from typing import List, Optional, Text, Tuple  # noqa: F401  # pylint: disable=unused-import
except ImportError:
    pass

from types import FrameType
from .browser import run_vnc_browser
from .config import config
from ._version import __version__

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
if sys.stderr.isatty():
    logging.addLevelName(logging.INFO, "\033[1;34m%s\033[1;0m" % logging.getLevelName(logging.INFO))


DOCKER_CONTAINER_NAME = "nojava-ipmi-kvmrc-{}".format(uuid.uuid4())


class WebserverNotReachableError(Exception):
    pass


class DockerNotInstalledError(Exception):
    pass


class DockerNotCallableError(Exception):
    pass


class DockerPortNotReadableError(Exception):
    pass


class DockerTerminatedError(Exception):
    pass


def running_macos():
    # type: () -> bool
    return platform.system() == "Darwin"


def is_command_available(command):
    # type: (Text) -> bool
    for path in os.environ["PATH"].split(os.pathsep):
        potential_command_path = os.path.join(path, command)
        if os.path.exists(potential_command_path) and os.access(potential_command_path, os.X_OK):
            return True
    return False


def view_kvm_console(
    hostname,
    login_user,
    login_password,
    login_endpoint,
    download_endpoint,
    allow_insecure_ssl,
    user_login_attribute_name,
    password_login_attribute_name,
    java_version,
    session_cookie_key=None,
):
    # type: (Text, Text, Text, Text, Text, bool, Text, Text, Text, Optional[Text]) -> None
    def add_sudo_if_configured(command_list):
        # type: (List[Text]) -> List[Text]
        if config.run_docker_with_sudo:
            command_list.insert(0, "sudo")
        return command_list

    def check_webserver(url):
        # type: (Text) -> None
        logging.info("Check if '%s' is reachable...", url)
        try:
            response = requests.head(url)
            response.raise_for_status()
            logging.info("The url '%s' is reachable.", url)
        except (requests.ConnectionError, requests.HTTPError):
            raise WebserverNotReachableError("The url '{}' is not reachable. Is the host down?".format(url))

    def check_docker():
        # type: () -> None
        with open(os.devnull, "w") as devnull:
            if not is_command_available("docker"):
                raise DockerNotInstalledError("Could not find the `docker` command. Please install Docker first.")
            if subprocess.call(add_sudo_if_configured(["docker", "ps"]), stdout=devnull, stderr=devnull) != 0:
                if running_macos():
                    subprocess.check_call(["open", "-g", "-a", "Docker"])
                    logging.info("Waiting for the Docker engine to be ready...")
                    while (
                        subprocess.call(add_sudo_if_configured(["docker", "ps"]), stdout=devnull, stderr=devnull) != 0
                    ):
                        time.sleep(1)
                else:
                    raise DockerNotCallableError(
                        "`docker` cannot be called. If `docker` needs `sudo`, please set `run_docker_with_sudo = True`"
                        " in your `~/.nojava-ipmi-kvmrc`."
                    )

    def run_docker():
        # type: () -> Tuple[subprocess.Popen, int]
        # TODO: pass variables as `extra_args` (?)
        environment_variables = [
            "-e",
            "XRES={}".format(config.x_resolution),
            "-e",
            "JAVA_VERSION={}".format(java_version),
        ]
        extra_args = [
            "-u",
            login_user,
            "-l",
            login_endpoint,
            "-d",
            download_endpoint,
            "-U",
            user_login_attribute_name,
            "-P",
            password_login_attribute_name,
            hostname,
        ]
        if session_cookie_key is not None:
            extra_args.extend(("-K", session_cookie_key))
        if allow_insecure_ssl:
            extra_args.insert(0, "-k")
        with open(os.devnull, "w") as devnull:
            logging.info("Starting the Docker container...")
            docker_process = subprocess.Popen(
                add_sudo_if_configured(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "-i",
                        "-P",
                        "-v",
                        "/etc/hosts:/etc/hosts:ro",
                        "--name",
                        DOCKER_CONTAINER_NAME,
                    ]
                )
                + environment_variables
                + [config.docker_image.format(version=__version__)]
                + extra_args,
                stdin=subprocess.PIPE,
                stdout=devnull,
                stderr=devnull,
            )
            if docker_process.stdin is not None:
                docker_process.stdin.write("{}\n".format(login_password).encode("utf-8"))
                docker_process.stdin.flush()
            else:
                # This case cannot happen (`if` is used to satisfy mypy)
                raise IOError("Something strange happened: Docker stdin not available.")
            while True:
                try:
                    if docker_process.poll() is not None:
                        raise DockerTerminatedError(
                            "Docker terminated with return code {}.".format(docker_process.returncode)
                        )
                    vnc_web_port = int(
                        subprocess.check_output(
                            add_sudo_if_configured(["docker", "port", DOCKER_CONTAINER_NAME]), stderr=devnull
                        )
                        .strip()
                        .split(b":")[1]
                    )
                    break
                except (IndexError, ValueError):
                    terminate_docker(docker_process)
                    raise DockerPortNotReadableError("Cannot read the exposted VNC web port.")
                except subprocess.CalledProcessError:
                    time.sleep(1)
        logging.info("Waiting for the Docker container to be up and ready...")
        while True:
            try:
                response = requests.head("http://localhost:{}".format(vnc_web_port))
                response.raise_for_status()
                break
            except (requests.ConnectionError, requests.HTTPError):
                if docker_process.poll() is not None:
                    raise DockerTerminatedError(
                        "Docker terminated with return code {}. Maybe you entered a wrong password?".format(
                            docker_process.returncode
                        )
                    )
                time.sleep(1)
        logging.info("Docker container is up and running.")
        return docker_process, vnc_web_port

    def terminate_docker(docker_process):
        # type: (subprocess.Popen) -> None
        if docker_process.poll() is None:
            with open(os.devnull, "w") as devnull:
                subprocess.check_call(
                    add_sudo_if_configured(["docker", "kill", DOCKER_CONTAINER_NAME]), stdout=devnull, stderr=devnull
                )

    def handle_sigint(sig, frame):
        # type: (int, FrameType) -> None
        terminate_docker(docker_process)
        sys.exit(0)

    check_webserver("http://{}/".format(hostname))
    check_docker()
    docker_process, vnc_web_port = run_docker()
    signal.signal(signal.SIGINT, handle_sigint)
    run_vnc_browser(
        "http://localhost:{}/vnc.html?host=localhost&port={}&autoconnect=true".format(vnc_web_port, vnc_web_port),
        hostname,
        tuple(int(c) for c in config.x_resolution.split("x")),
    )
    terminate_docker(docker_process)
