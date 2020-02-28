import atexit
import logging
import os
import platform
import requests
import signal
import subprocess
import sys
import uuid
import re

import asyncio

try:
    from typing import List, Optional, Text, Tuple  # noqa: F401  # pylint: disable=unused-import
except ImportError:
    pass

from types import FrameType
from .utils import generate_temp_password
from .config import config
from ._version import __version__

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
if sys.stderr.isatty():
    logging.addLevelName(logging.INFO, "\033[1;34m%s\033[1;0m" % logging.getLevelName(logging.INFO))




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

class KvmViewer:
    def __init__(self, url, external_vnc_dns, vnc_web_port, vnc_password, kill_process):
        self._url = url
        self._external_vnc_dns = external_vnc_dns
        self._vnc_web_port = vnc_web_port
        self._vnc_password = vnc_password
        self._kill_process = kill_process
        self._already_killed = False

        atexit.register(self.kill_process)

    @property
    def url(self):
        return self._url

    @property
    def external_vnc_dns(self):
        return self._external_vnc_dns

    @property
    def vnc_web_port(self):
        return self._vnc_web_port

    @property
    def vnc_password(self):
        return self._vnc_password

    def kill_process(self):
        if self._already_killed:
            return
        self._already_killed = True
        return self._kill_process()

async def start_kvm_container(
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
    external_vnc_dns='localhost',
    docker_port=None,
    additional_logging=None,
    selected_resolution=None,
):
    # type: (Text, Text, Text, Text, Text, bool, Text, Text, Text, Optional[Text]) -> None
    def log(msg, *args, **kwargs):
        logging.info(msg, *args, **kwargs)
        if additional_logging is not None:
            additional_logging(msg, *args, **kwargs)

    DOCKER_CONTAINER_NAME = "nojava-ipmi-kvmrc-{}".format(uuid.uuid4())
    def add_sudo_if_configured(command_list):
        # type: (List[Text]) -> List[Text]
        if config.run_docker_with_sudo:
            command_list.insert(0, "sudo")
        return command_list

    async def check_webserver(url):
        # type: (Text) -> None
        log("Check if '%s' is reachable...", url)
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, requests.head, url)
            response.raise_for_status()
            log("The url '%s' is reachable.", url)
        except (requests.ConnectionError, requests.HTTPError):
            raise WebserverNotReachableError("The url '{}' is not reachable. Is the host down?".format(url))

    async def check_docker():
        # type: () -> None
        with open(os.devnull, "w") as devnull:
            if not is_command_available("docker"):
                raise DockerNotInstalledError("Could not find the `docker` command. Please install Docker first.")
            if subprocess.call(add_sudo_if_configured(["docker", "ps"]), stdout=devnull, stderr=devnull) != 0:
                if running_macos():
                    subprocess.check_call(["open", "-g", "-a", "Docker"])
                    log("Waiting for the Docker engine to be ready...")
                    while (
                        subprocess.call(add_sudo_if_configured(["docker", "ps"]), stdout=devnull, stderr=devnull) != 0
                    ):
                        await asyncio.sleep(1)
                else:
                    raise DockerNotCallableError(
                        "`docker` cannot be called. If `docker` needs `sudo`, please set `run_docker_with_sudo = True`"
                        " in your `~/.nojava-ipmi-kvmrc`."
                    )

    async def run_docker():
        # type: () -> Tuple[subprocess.Popen, int]
        # TODO: pass variables as `extra_args` (?)
        nonlocal selected_resolution
        vnc_password = generate_temp_password(20)
        if selected_resolution is None:
            selected_resolution = config.x_resolution
        if not re.match(r'^[1-9][0-9]{2,3}x[1-9][0-9]{2,3}$', selected_resolution):
            selected_resolution = '1600x1200'
        environment_variables = [
            "-e",
            "XRES={}".format(selected_resolution),
            "-e",
            "JAVA_VERSION={}".format(java_version),
            "-e",
            "VNC_PASSWD={}".format(vnc_password),
            "-e",
            "KVM_HOSTNAME={}".format(hostname)
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
            log("Starting the Docker container...")
            docker_process = subprocess.Popen(
                add_sudo_if_configured(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "-i",
                        "-v",
                        "/etc/hosts:/etc/hosts:ro",
                        "--name",
                        DOCKER_CONTAINER_NAME,
                    ]
                )
                + environment_variables
                + ([
                    "-P"
                ] if docker_port is None else [
                    "-p",
                    "{}:8080".format(docker_port),
                ])
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
                    await asyncio.sleep(1)

        log("Waiting for the Docker container to be up and ready...")
        while True:
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, requests.head, "http://{}:{}".format(external_vnc_dns, vnc_web_port))
                response.raise_for_status()
                break
            except (requests.ConnectionError, requests.HTTPError):
                if docker_process.poll() is not None:
                    raise DockerTerminatedError(
                        "Docker terminated with return code {}. Maybe you entered a wrong password?".format(
                            docker_process.returncode
                        )
                    )
                await asyncio.sleep(1)

        log("Docker container is up and running.")
        return docker_process, vnc_web_port, vnc_password

    def terminate_docker(docker_process):
        # type: (subprocess.Popen) -> None
        if docker_process.poll() is None:
            with open(os.devnull, "w") as devnull:
                subprocess.check_call(
                    add_sudo_if_configured(["docker", "kill", DOCKER_CONTAINER_NAME]), stdout=devnull, stderr=devnull
                )
        log("Docker container was terminated.")

    await check_webserver("http://{}/".format(hostname))
    await check_docker()
    docker_process, vnc_web_port, vnc_password = await run_docker()

    url = "http://{}:{}/vnc.html?host={}&port={}&autoconnect=true&password={}".format(external_vnc_dns, vnc_web_port, external_vnc_dns, vnc_web_port, vnc_password)
    log("Url to view kvm console: {}".format(url))

    return KvmViewer(url, external_vnc_dns, vnc_web_port, vnc_password, lambda: terminate_docker(docker_process))
