import atexit
import logging
import os
import platform
import requests
import subprocess
import uuid
import re

import asyncio

try:
    from typing import Any, Callable, List, Optional, Text, Tuple  # noqa: F401  # pylint: disable=unused-import
except ImportError:
    pass

from .utils import generate_temp_password
from .config import config, HostConfig, HTML5HostConfig, JavaHostConfig
from ._version import __version__

logger = logging.getLogger(__name__)


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
    def __init__(self, url, external_vnc_dns, web_port, kill_process):
        self._url = url
        self._external_vnc_dns = external_vnc_dns
        self._web_port = web_port
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
    def web_port(self):
        return self._web_port

    def kill_process(self):
        if self._already_killed:
            return
        self._already_killed = True
        return self._kill_process()


class JavaKvmViewer(KvmViewer):
    def __init__(self, url, external_vnc_dns, web_port, kill_process, vnc_password):
        super().__init__(url, external_vnc_dns, web_port, kill_process)
        self._vnc_password = vnc_password

    @property
    def vnc_password(self):
        return self._vnc_password


class HTML5KvmViewer(KvmViewer):
    def __init__(
        self,
        url,
        external_vnc_dns,
        web_port,
        kill_process,
        subdir,
        authorization_key,
        authorization_value,
        html5_endpoint,
    ):
        super().__init__(url, external_vnc_dns, web_port, kill_process)
        self._subdir = subdir
        self._authorization_key = authorization_key
        self._authorization_value = authorization_value
        self._html5_endpoint = html5_endpoint

    @property
    def subdir(self):
        return self._subdir

    @property
    def authorization_key(self):
        return self._authorization_key

    @property
    def authorization_value(self):
        return self._authorization_value

    @property
    def html5_endpoint(self):
        return self._html5_endpoint


def log_factory(additional_logging):
    def log(msg, *args, **kwargs):
        logger.info(msg, *args, **kwargs)
        if additional_logging is not None:
            additional_logging(msg, *args, **kwargs)

    return log


def add_sudo_if_configured(command_list):
    # type: (List[Text]) -> List[Text]
    if config.run_docker_with_sudo:
        command_list.insert(0, "sudo")
    return command_list


async def check_webserver(log, url):
    # type: (Callable, Text) -> None
    log("Check if '%s' is reachable...", url)
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, requests.head, url)
        response.raise_for_status()
        log("The url '%s' is reachable.", url)
    except (requests.ConnectionError, requests.HTTPError):
        raise WebserverNotReachableError("The url '{}' is not reachable. Is the host down?".format(url))


async def check_docker(log, subprocess_output):
    # type: (Callable, Optional[int]) -> None
    if not is_command_available("docker"):
        raise DockerNotInstalledError("Could not find the `docker` command. Please install Docker first.")
    if (
        subprocess.call(add_sudo_if_configured(["docker", "ps"]), stdout=subprocess_output, stderr=subprocess_output)
        != 0
    ):
        if running_macos():
            subprocess.check_call(["open", "-g", "-a", "Docker"])
            log("Waiting for the Docker engine to be ready...")
            while (
                subprocess.call(
                    add_sudo_if_configured(["docker", "ps"]), stdout=subprocess_output, stderr=subprocess_output
                )
                != 0
            ):
                await asyncio.sleep(1)
        else:
            raise DockerNotCallableError(
                "`docker` cannot be called. If `docker` needs `sudo`, please set `run_docker_with_sudo = True`"
                " in your `~/.nojava-ipmi-kvmrc`."
            )


def create_extra_args(host_config):
    # type: (HostConfig) -> List
    extra_args = [
        "-u",
        host_config.login_user,
        "-l",
        host_config.login_endpoint,
        "-U",
        host_config.user_login_attribute_name,
        "-P",
        host_config.password_login_attribute_name,
        host_config.full_hostname,
    ]
    if host_config.extra_login_form_fields is not None:
        extra_args.extend(("-e", host_config.extra_login_form_fields))
    if host_config.session_cookie_key is not None:
        extra_args.extend(("-K", host_config.session_cookie_key))
    if host_config.skip_login:
        extra_args.insert(0, "-s")
    if host_config.send_post_data_as_json:
        extra_args.insert(0, "-j")
    if host_config.allow_insecure_ssl:
        extra_args.insert(0, "-k")

    return extra_args


def create_java_docker_args(host_config, login_password, selected_resolution):
    # type: (JavaHostConfig, Optional[Text], Optional[Text]) -> Tuple[List, List, Text, Text, Text]
    # extra-program-args, env variables, docker image, stdin
    vnc_password = generate_temp_password(20)
    if selected_resolution is None:
        selected_resolution = config.x_resolution
    if not re.match(r"^[1-9][0-9]{2,3}x[1-9][0-9]{2,3}$", selected_resolution):
        selected_resolution = "1600x1200"

    extra_args = ["-d", host_config.download_endpoint]
    extra_args.extend(create_extra_args(host_config))

    if host_config.format_jnlp:
        extra_args.insert(0, "-f")

    environment_variables = [
        "-e",
        "XRES={}".format(selected_resolution),
        "-e",
        "JAVA_VERSION={}".format(host_config.java_version),
        "-e",
        "VNC_PASSWD={}".format(vnc_password),
        "-e",
        "KVM_HOSTNAME={}".format(host_config.full_hostname),
    ]
    java_provider = "oraclejre" if host_config.java_version.endswith("-oracle") else "openjdk"
    java_major_version = host_config.java_version.split("u")[0]

    return (
        extra_args,
        environment_variables,
        config.java_docker_image.format(
            version=__version__, java_provider=java_provider, java_major_version=java_major_version
        ),
        login_password if login_password is not None else "",
        vnc_password,
    )


def create_html5_docker_args(
    host_config, login_password, authorization_key=None, authorization_value=None, subdir=None
):
    # type: (HTML5HostConfig, Optional[Text], Optional[Text], Optional[Text], Optional[Text]) -> Tuple[List, List, Text, Text]
    # extra-program-args, env variables, docker image, stdin
    extra_args = create_extra_args(host_config)

    environment_variables = ["-e", "KVM_HOSTNAME={}".format(host_config.full_hostname)]
    return (
        extra_args,
        environment_variables,
        config.html5_docker_image.format(version=__version__),
        host_config.get_config_json(login_password, subdir, authorization_key, authorization_value),
    )


async def start_kvm_container(
    host_config,
    login_password,
    external_vnc_dns="localhost",
    docker_port=None,
    additional_logging=None,
    selected_resolution=None,
    authorization_key=None,
    authorization_value=None,
    subdir=None,
    debug=False,
):
    # type: (HostConfig, Optional[Text], Text, Optional[int], Optional[Callable[..., None]], Optional[Text], Optional[Text], Optional[Text], Optional[Text], bool) -> KvmViewer
    if not isinstance(host_config, (JavaHostConfig, HTML5HostConfig)):
        raise ValueError("Invalid host config class")

    log = log_factory(additional_logging)

    subprocess_output = None if debug else subprocess.DEVNULL

    await check_webserver(log, "http://{}/".format(host_config.full_hostname))
    await check_docker(log, subprocess_output)

    # TODO: pass variables as `extra_args` (?)
    DOCKER_CONTAINER_NAME = "nojava-ipmi-kvmrc-{}".format(uuid.uuid4())

    if isinstance(host_config, JavaHostConfig):
        extra_args, environment_variables, docker_image, stdin, vnc_password = create_java_docker_args(
            host_config, login_password, selected_resolution
        )
    elif isinstance(host_config, HTML5HostConfig):
        extra_args, environment_variables, docker_image, stdin = create_html5_docker_args(
            host_config, login_password, authorization_key, authorization_value, subdir
        )

    log("Starting the Docker container...")
    docker_process = subprocess.Popen(
        add_sudo_if_configured(
            ["docker", "run", "-i", "-v", "/etc/hosts:/etc/hosts:ro", "--rm", "--name", DOCKER_CONTAINER_NAME]
        )
        + environment_variables
        + (["-P"] if docker_port is None else ["-p", "{}:8080".format(docker_port)])
        + [docker_image]
        + extra_args,
        stdin=subprocess.PIPE,
        stdout=subprocess_output,
        stderr=subprocess_output,
    )
    if docker_process.stdin is not None:
        docker_process.stdin.write("{}\n".format(stdin).encode("utf-8"))
        docker_process.stdin.flush()
        docker_process.stdin.close()
    else:
        # This case cannot happen (`if` is used to satisfy mypy)
        raise IOError("Something strange happened: Docker stdin not available.")

    def terminate_docker():
        # type: () -> None
        nonlocal docker_process
        if docker_process.poll() is None:
            subprocess.check_call(
                add_sudo_if_configured(["docker", "kill", DOCKER_CONTAINER_NAME]),
                stdout=subprocess_output,
                stderr=subprocess_output,
            )
        log("Docker container was terminated.")

    while True:
        try:
            if docker_process.poll() is not None:
                raise DockerTerminatedError("Docker terminated with return code {}.".format(docker_process.returncode))
            web_port = int(
                subprocess.check_output(
                    add_sudo_if_configured(["docker", "port", DOCKER_CONTAINER_NAME]), stderr=subprocess_output
                )
                .strip()
                .split(b"\n")[0].split(b":")[1]
            )
            break
        except (IndexError, ValueError):
            terminate_docker()
            raise DockerPortNotReadableError("Cannot read the VNC web port.")
        except subprocess.CalledProcessError:
            await asyncio.sleep(1)

    log("Waiting for the Docker container to be up and ready...")
    loop = asyncio.get_event_loop()

    def get():
        nonlocal external_vnc_dns, web_port, authorization_key, authorization_value
        cookies = {}
        if authorization_key is not None and authorization_value is not None:
            cookies[authorization_key] = authorization_value
        return requests.head("http://{}:{}".format(external_vnc_dns, web_port), cookies=cookies)

    while True:
        try:
            response = await loop.run_in_executor(None, get)
            response.raise_for_status()
            break
        except (requests.ConnectionError, requests.HTTPError):
            if docker_process.poll() is not None:
                if not host_config.skip_login:
                    raise DockerTerminatedError(
                        "Docker terminated with return code {}. Maybe you entered a wrong password?".format(
                            docker_process.returncode
                        )
                    )
                else:
                    raise DockerTerminatedError(
                        (
                            "Docker terminated with return code {}."
                            + " Maybe you configured a wrong download endpoint or need a login?"
                        ).format(docker_process.returncode)
                    )
            await asyncio.sleep(1)

    log("Docker container is up and running.")

    if isinstance(host_config, JavaHostConfig):
        url = "http://{ext_dns}:{web_port}/vnc.html?host={ext_dns}&port={web_port}&autoconnect=true&password={password}".format(
            ext_dns=external_vnc_dns, password=vnc_password, web_port=web_port
        )
        log("Url to view kvm console: {}".format(url))
        return JavaKvmViewer(url, external_vnc_dns, web_port, terminate_docker, vnc_password)
    elif isinstance(host_config, HTML5HostConfig):
        url = "http://{}:{}/{}".format(external_vnc_dns, web_port, host_config.html5_endpoint)
        log("Url to view kvm console: {}".format(url))
        return HTML5KvmViewer(
            url,
            external_vnc_dns,
            web_port,
            terminate_docker,
            subdir,
            authorization_key,
            authorization_value,
            host_config.html5_endpoint,
        )
    else:
        assert False  # Type is checked at the top of function


__all__ = [
    "DockerNotCallableError",
    "DockerNotInstalledError",
    "DockerPortNotReadableError",
    "DockerTerminatedError",
    "WebserverNotReachableError",
    "start_kvm_container",
]
