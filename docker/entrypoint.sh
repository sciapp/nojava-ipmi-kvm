#!/bin/bash

read -r -s PASSWD
echo "${PASSWD}" | /usr/local/bin/get_java_viewer -o /tmp/launch.jnlp "$@"
return_code="$?"
if [[ "${return_code}" -ne 0 ]]; then
    exit "${return_code}"
fi

# Replace variables in `/etc/supervisord.conf`
for v in XRES; do
    eval sed -i "s/{$v}/\$$v/" /etc/supervisor/conf.d/supervisord.conf
done

# Install needed Java version
: ${JAVA_VERSION:=7u181}
pushd "/opt/java_packages/${JAVA_VERSION}" >/dev/null 2>&1 && \
dpkg -i *.deb && \
popd >/dev/null 2>&1 && \
pushd "/opt/icedtea" >/dev/null 2>&1 && \
dpkg -i *.deb && \
popd >/dev/null 2>&1

/usr/bin/supervisord
