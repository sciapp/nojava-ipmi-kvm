import copy
import os
from configparser import ConfigParser

try:
    from typing import Any, Dict, Optional, Text, TextIO, Union  # noqa: F401  # pylint: disable=unused-import
except ImportError:
    pass

DEFAULT_CONFIG_FILEPATH = "~/.nojava-ipmi-kvmrc"


class InvalidHostnameError(Exception):
    pass


class HostConfig(object):
    def __init__(
        self,
        short_hostname,
        full_hostname,
        skip_login,
        login_user,
        login_endpoint,
        download_endpoint,
        allow_insecure_ssl,
        user_login_attribute_name,
        password_login_attribute_name,
        java_version,
        format_jnlp,
        send_post_data_as_json,
        extra_login_form_fields,
        session_cookie_key,
    ):
        # type: (Text, Text, bool, Text, Text, Text, bool, Text, Text, Text, bool, bool, Optional[Text], Optional[Text]) -> None
        self._short_hostname = short_hostname
        self._full_hostname = full_hostname
        self._skip_login = skip_login
        self._login_user = login_user
        self._login_endpoint = login_endpoint
        self._download_endpoint = download_endpoint
        self._allow_insecure_ssl = allow_insecure_ssl
        self._user_login_attribute_name = user_login_attribute_name
        self._password_login_attribute_name = password_login_attribute_name
        self._java_version = java_version
        self._format_jnlp = format_jnlp
        self._send_post_data_as_json = send_post_data_as_json
        self._extra_login_form_fields = extra_login_form_fields
        self._session_cookie_key = session_cookie_key

    @property
    def short_hostname(self):
        # type: () -> Text
        return self._short_hostname

    @property
    def full_hostname(self):
        # type: () -> Text
        return self._full_hostname

    @property
    def skip_login(self):
        # type: () -> bool
        return self._skip_login

    @property
    def login_user(self):
        # type: () -> Text
        return self._login_user

    @property
    def login_endpoint(self):
        # type: () -> Text
        return self._login_endpoint

    @property
    def download_endpoint(self):
        # type: () -> Text
        return self._download_endpoint

    @property
    def allow_insecure_ssl(self):
        # type: () -> bool
        return self._allow_insecure_ssl

    @property
    def user_login_attribute_name(self):
        # type: () -> Text
        return self._user_login_attribute_name

    @property
    def password_login_attribute_name(self):
        # type: () -> Text
        return self._password_login_attribute_name

    @property
    def java_version(self):
        # type: () -> Text
        return self._java_version

    @property
    def format_jnlp(self):
        # type: () -> bool
        return self._format_jnlp

    @property
    def send_post_data_as_json(self):
        # type: () -> bool
        return self._send_post_data_as_json

    @property
    def extra_login_form_fields(self):
        # type: () -> Optional[Text]
        return self._extra_login_form_fields

    @property
    def session_cookie_key(self):
        # type: () -> Optional[Text]
        return self._session_cookie_key


class Config(object):
    _default_config = {
        "general": {
            "docker_image": "sciapp/nojava-ipmi-kvm:v{version}-{java_provider}-{java_major_version}",
            "run_docker_with_sudo": False,
            "x_resolution": "1024x768",
        }
    }  # type: Dict[Text, Dict[Text, Any]]
    _default_host_config = {
        "skip_login": False,
        "login_user": "ADMIN",
        "login_endpoint": "cgi/login.cgi",
        "download_endpoint": "cgi/url_redirect.cgi?url_name=ikvm&url_type=jwsk",
        "allow_insecure_ssl": False,
        "user_login_attribute_name": "name",
        "password_login_attribute_name": "pwd",
        "java_version": "7u181",
        "format_jnlp": False,
        "send_post_data_as_json": False,
        "extra_login_form_fields": None,
        "session_cookie_key": None,
    }  # type: Dict[Text, Any]

    @classmethod
    def write_default_config(cls, config_filepath_or_file):
        # type: (Union[Text, TextIO]) -> None
        default_config = ConfigParser()
        default_config.read_dict(cls._default_config)
        if isinstance(config_filepath_or_file, Text):
            with open(config_filepath_or_file, "w", encoding="utf-8") as config_file:
                default_config.write(config_file)
        else:
            config_file = config_filepath_or_file
            default_config.write(config_file)

    def __init__(self, config_filepath=DEFAULT_CONFIG_FILEPATH):
        # type: (Optional[Text]) -> None
        self._config_filepath = config_filepath
        self._config = ConfigParser()
        self._config.read_dict(self._default_config)
        self.read_config()

    def read_config(self, config_filepath=None):
        # type: (Optional[Text]) -> None
        if config_filepath is not None:
            self._config_filepath = config_filepath
        if self._config_filepath is not None:
            self._config.read(os.path.abspath(os.path.expanduser(self._config_filepath)))

    def __getitem__(self, item):
        # type: (Text) -> HostConfig
        try:
            host_config = copy.deepcopy(self._default_host_config)
            host_config["short_hostname"] = item
            type_to_method = {
                bool: self._config.getboolean,
                float: self._config.getfloat,
                int: self._config.getint,
            }
            for k, v in self._config[item].items():
                method = type_to_method.get(type(host_config.get(k, None)), self._config.get)
                host_config[k] = method(item, k)
            return HostConfig(**host_config)
        except KeyError:
            raise InvalidHostnameError(
                "{} is not present in the configuration. Please insert a host entry in '{}'.".format(
                    item, self._config_filepath
                )
            )

    def get_servers(self):
        sections = self._config.sections()
        sections.remove("general")
        return sections

    @property
    def docker_image(self):
        # type: () -> Text
        return self._config["general"]["docker_image"]

    @property
    def run_docker_with_sudo(self):
        # type: () -> bool
        return self._config["general"].getboolean("run_docker_with_sudo")

    @property
    def x_resolution(self):
        # type: () -> Text
        return self._config["general"]["x_resolution"]


config = Config(None)
