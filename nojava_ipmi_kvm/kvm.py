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
    from typing import Text  # noqa: F401  # pylint: disable=unused-import
except ImportError:
    pass

from types import FrameType
from .browser import run_vnc_browser
from .config import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
if sys.stderr.isatty():
    logging.addLevelName(logging.INFO, "\033[1;34m%s\033[1;0m" % logging.getLevelName(logging.INFO))


DOCKER_CONTAINER_NAME = "nojava-ipmi-kvmrc-{}".format(uuid.uuid4())


class DockerNotInstalledError(Exception):
    pass


class DockerNotCallableError(Exception):
    pass


class DockerTerminatedError(Exception):
    pass


def running_macos():
    # type: () -> bool
    return platform.system() == "Darwin"


def view_kvm_console(
    hostname,
    login_user,
    login_password,
    login_endpoint,
    download_endpoint,
    allow_insecure_ssl,
    user_login_attribute_name,
    password_login_attribute_name,
):
    # type: (Text, Text, Text, Text, Text, bool, Text, Text) -> None
    def check_docker():
        # type: () -> None
        with open(os.devnull, "w") as devnull:
            if subprocess.call(["command", "-v", "docker"], stdout=devnull, stderr=devnull) != 0:
                raise DockerNotInstalledError("Could not find the `docker` command. Please install Docker first.")
            if subprocess.call(["docker", "ps"], stdout=devnull, stderr=devnull) != 0:
                if running_macos():
                    subprocess.check_call(["open", "-g", "-a", "Docker"])
                    logging.info("Waiting for the Docker engine to be ready...")
                    while subprocess.call(["docker", "ps"], stdout=devnull, stderr=devnull) != 0:
                        time.sleep(1)
                else:
                    raise DockerNotCallableError(
                        "`docker` cannot be called. Maybe you are not allowed to call `docker` directly?"
                    )

    def run_docker():
        # type: () -> subprocess.Popen
        environment_variables = [
            "-e",
            "XRES={}".format(config.x_resolution),
            "-e",
            "VNC_WEBPORT={}".format(config.vnc_web_port),
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
        if allow_insecure_ssl:
            extra_args.insert(0, "-k")
        with open(os.devnull, "w") as devnull:
            logging.info("Starting the Docker container...")
            docker_process = subprocess.Popen(
                [
                    "docker",
                    "run",
                    "-i",
                    "-p",
                    "{}:{}".format(config.vnc_web_port, config.vnc_web_port),
                    "--name",
                    DOCKER_CONTAINER_NAME,
                ]
                + environment_variables
                + [config.docker_image]
                + extra_args,
                stdin=subprocess.PIPE,
                stdout=devnull,
                stderr=devnull,
            )
            if docker_process.stdin is not None:
                docker_process.stdin.write("{}\n".format(login_password))
                docker_process.stdin.flush()
            else:
                # This case cannot happen (`if` is used to satisfy mypy)
                raise IOError("Something strange happened: Docker stdin not available.")
        logging.info("Waiting for the Docker container to be up and ready...")
        while True:
            try:
                response = requests.get("http://localhost:{}".format(config.vnc_web_port))
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
        return docker_process

    def terminate_docker(docker_process):
        # type: (subprocess.Popen) -> None
        if docker_process.poll() is None:
            with open(os.devnull, "w") as devnull:
                subprocess.check_call(["docker", "kill", DOCKER_CONTAINER_NAME], stdout=devnull, stderr=devnull)

    def handle_sigint(sig, frame):
        # type: (int, FrameType) -> None
        terminate_docker(docker_process)
        sys.exit(0)

    check_docker()
    docker_process = run_docker()
    signal.signal(signal.SIGINT, handle_sigint)
    run_vnc_browser(
        "http://localhost:{}/vnc.html?host=localhost&port={}&autoconnect=true".format(
            config.vnc_web_port, config.vnc_web_port
        ),
        tuple(int(c) for c in config.x_resolution.split("x")),
    )
    terminate_docker(docker_process)
