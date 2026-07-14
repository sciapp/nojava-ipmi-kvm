import logging
import subprocess

try:
    from typing import Any, Callable, Optional  # noqa: F401  # pylint: disable=unused-import
except ImportError:
    pass

from .config import config

logger = logging.getLogger(__name__)

CHILD_NAME_PREFIX = "nojava-ipmi-kvmrc-"


def _add_sudo_if_configured(command_list):
    if config.run_docker_with_sudo:
        command_list.insert(0, "sudo")
    return command_list


def _port_in_range(port, port_start, port_end):
    if port is None:
        return False
    try:
        port_value = int(port)
    except (TypeError, ValueError):
        return False
    return port_start <= port_value < port_end


def cleanup_stale_kvm_children(port_start, port_end, log=None):
    # type: (int, int, Optional[Callable[..., None]]) -> None
    log_func = log if log is not None else logger.info

    list_result = subprocess.run(
        _add_sudo_if_configured(
            ["docker", "ps", "-aq", "--filter", "name={}".format(CHILD_NAME_PREFIX)]
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        universal_newlines=True,
        check=False,
    )

    for container_id in list_result.stdout.split():
        container_id = container_id.strip()
        if not container_id:
            continue

        state_result = subprocess.run(
            _add_sudo_if_configured(["docker", "inspect", "-f", "{{.State.Status}}", container_id]),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
            check=False,
        )
        state = state_result.stdout.strip()

        name_result = subprocess.run(
            _add_sudo_if_configured(["docker", "inspect", "-f", "{{.Name}}", container_id]),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
            check=False,
        )
        name = name_result.stdout.strip().lstrip("/")

        if state in ("exited", "dead"):
            remove_result = subprocess.run(
                _add_sudo_if_configured(["docker", "rm", "-f", container_id]),
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if remove_result.returncode == 0:
                log_func("Removed exited child {}".format(name))
            continue

        port_result = subprocess.run(
            _add_sudo_if_configured(["docker", "port", container_id, "8080/tcp"]),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
            check=False,
        )
        host_port = None
        if port_result.returncode == 0 and port_result.stdout.strip():
            host_port = port_result.stdout.strip().splitlines()[0].rsplit(":", 1)[-1]

        if _port_in_range(host_port, port_start, port_end):
            remove_result = subprocess.run(
                _add_sudo_if_configured(["docker", "rm", "-f", container_id]),
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if remove_result.returncode == 0:
                log_func(
                    "Removed stale child {} (port {}, range {}-{})".format(
                        name, host_port, port_start, port_end - 1
                    )
                )
