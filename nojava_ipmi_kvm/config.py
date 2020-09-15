import os
import yaml
import json

try:
    from typing import Any, Dict, List, Optional, Text, TextIO, Union  # noqa: F401  # pylint: disable=unused-import
except ImportError:
    pass

from .utils import update

DEFAULT_CONFIG_FILEPATH = "~/.nojava-ipmi-kvmrc.yaml"


class InvalidHostnameError(Exception):
    pass


class HostConfig(object):
    def __init__(
        self,
        short_hostname,
        full_hostname,
        skip_login=False,
        login_user="ADMIN",
        login_endpoint="cgi/login.cgi",
        allow_insecure_ssl=False,
        user_login_attribute_name="name",
        password_login_attribute_name="pwd",
        send_post_data_as_json=False,
        extra_login_form_fields=None,
        session_cookie_key=None,
    ):
        # type: (Text, Text, bool, Text, Text, bool, Text, Text, bool, Optional[Text], Optional[Text]) -> None
        self._short_hostname = short_hostname
        self._full_hostname = full_hostname
        self._skip_login = skip_login
        self._login_user = login_user
        self._login_endpoint = login_endpoint
        self._allow_insecure_ssl = allow_insecure_ssl
        self._user_login_attribute_name = user_login_attribute_name
        self._password_login_attribute_name = password_login_attribute_name
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


class JavaHostConfig(HostConfig):
    def __init__(
        self,
        short_hostname,
        full_hostname,
        download_endpoint="cgi/url_redirect.cgi?url_name=ikvm&url_type=jwsk",
        java_version="7u181",
        format_jnlp=False,
        **kwargs,
    ):
        # type: (Text, Text, Text, Text, bool, **Any) -> None
        super().__init__(short_hostname, full_hostname, **kwargs)
        self._download_endpoint = download_endpoint
        self._java_version = java_version
        self._format_jnlp = format_jnlp

    @property
    def download_endpoint(self):
        # type: () -> Text
        return self._download_endpoint

    @property
    def java_version(self):
        # type: () -> Text
        return self._java_version

    @property
    def format_jnlp(self):
        # type: () -> bool
        return self._format_jnlp


class HTML5HostConfig(HostConfig):
    def __init__(
        self,
        short_hostname,
        full_hostname,
        html5_endpoint="cgi/url_redirect.cgi?url_name=man_ikvm_html5_bootstrap",
        rewrites=None,
        **kwargs,
    ):
        # type: (Text, Text, Text, List, **Any) -> None
        super().__init__(short_hostname, full_hostname, **kwargs)
        self._html5_endpoint = html5_endpoint
        self._rewrites = [] if rewrites is None else rewrites

    @property
    def html5_endpoint(self):
        # type: () -> Text
        return self._html5_endpoint

    @property
    def rewrites(self):
        # type: () -> List
        return self._rewrites

    def get_config_json(self, kvm_password, subdir, authorization_key=None, authorization_value=None):
        rewrites = [dict(x) for x in self._rewrites]  # Create shallow copy, we want the dicts to be reusable
        for x in rewrites:
            x["replace"] = x["replace"].replace("{subdirectory}", subdir if subdir is not None else "")

        input_config = {"rewrites": rewrites, "kvm_host": "https://" + self.full_hostname, "kvm_password": kvm_password}

        if authorization_key is not None and authorization_value is not None:
            input_config["authorization"] = {"key": authorization_key, "value": authorization_value}

        return json.dumps(input_config)


class Config(object):
    @classmethod
    def write_default_config(cls, config_filepath_or_file):
        # type: (Union[Text, TextIO]) -> None
        conf = cls(None)
        conf.write(config_filepath_or_file)

    def __init__(self, config_filepath=DEFAULT_CONFIG_FILEPATH):
        # type: (Optional[Text]) -> None
        self._config_filepath = config_filepath
        self.read_config()

    def write(self, config_filepath_or_file):
        # type: (Union[Text, TextIO]) -> None

        if isinstance(config_filepath_or_file, Text):
            with open(config_filepath_or_file, "w", encoding="utf-8") as config_file:
                yaml.dump(self._config_dict, config_file, default_flow_style=False)
        else:
            config_file = config_filepath_or_file
            yaml.dump(self._config_dict, config_file, default_flow_style=False)

    def read_config(self, config_filepath=None):
        # type: (Optional[Text]) -> None
        # Set defaults
        self._config_dict = {
            "general": {
                "java_docker_image": "sciapp/nojava-ipmi-kvm:v{version}-{java_provider}-{java_major_version}",
                "html5_docker_image": "sciapp/nojava-ipmi-kvm:v{version}-html5",
                "run_docker_with_sudo": False,
                "x_resolution": "1024x768",
            },
            "templates": {},
            "hosts": {},
        }

        # load values
        if config_filepath is not None:
            self._config_filepath = config_filepath
        if self._config_filepath is not None:
            with open(os.path.abspath(os.path.expanduser(self._config_filepath)), "r") as f:
                self._config_dict = update(self._config_dict, yaml.safe_load(f)) # recursive upadte

    def __getitem__(self, item):
        # type: (Text) -> HostConfig
        try:
            host_config = {}

            raw_host = self._config_dict["hosts"][item]
            if "based_on" in raw_host and raw_host["based_on"] in self._config_dict["templates"]:
                for k, v in self._config_dict["templates"][raw_host["based_on"]].items():
                    host_config[k] = v

            host_config["short_hostname"] = item

            host_config.update(raw_host)
            del host_config["based_on"]

            if "html5_endpoint" in host_config:
                return HTML5HostConfig(**host_config)
            else:
                return JavaHostConfig(**host_config)
        except KeyError:
            raise InvalidHostnameError(
                "{} is not present in the configuration. Please insert a host entry in '{}'.".format(
                    item, self._config_filepath
                )
            )

    def get_servers(self):
        return self._config_dict['hosts'].keys()

    @property
    def java_docker_image(self):
        # type: () -> Text
        return self._config_dict["general"]["java_docker_image"]

    @property
    def html5_docker_image(self):
        # type: () -> Text
        return self._config_dict["general"]["html5_docker_image"]

    @property
    def run_docker_with_sudo(self):
        # type: () -> bool
        return self._config_dict["general"]["run_docker_with_sudo"]

    @property
    def x_resolution(self):
        # type: () -> Text
        return self._config_dict["general"]["x_resolution"]


config = Config(None)
