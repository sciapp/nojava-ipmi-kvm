#!/usr/bin/env python3

from configparser import ConfigParser
import yaml  # needs the `pyyaml` package
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: {} <input-rc> [output-rc.yaml]".format(sys.argv[0]))
        sys.exit(1)

    old_config = ConfigParser()
    old_config.read(sys.argv[1])

    global_renamed_fields = {"docker_image": "java_docker_image"}
    global_bool_fields = ["run_docker_with_sudo"]
    host_bool_fields = ["skip_login", "allow_insecure_ssl", "format_jnlp", "send_post_data_as_json"]

    config = {}
    general = {global_renamed_fields.get(key, key): value for key, value in old_config["general"].items()}
    for x in global_bool_fields:
        if x in general:
            general[x] = old_config["general"].getboolean(x)

    config["general"] = general

    config["hosts"] = {}

    for x in old_config.sections():
        if x == "general":
            continue

        config["hosts"][x] = dict(old_config[x])
        for y in host_bool_fields:
            if y in config["hosts"][x]:
                config["hosts"][x][y] = old_config[x].getboolean(y)

    if len(sys.argv) > 2:
        with open(sys.argv[2], "w") as stream:
            yaml.dump(config, stream, default_flow_style=False)
    else:
        print(yaml.dump(config, default_flow_style=False))


if __name__ == "__main__":
    main()
