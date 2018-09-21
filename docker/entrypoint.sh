#!/bin/bash

read -r -s PASSWD
echo "${PASSWD}" | /usr/local/bin/get_java_viewer -o /tmp/launch.jnlp "$@"

/usr/bin/supervisord
