#!/bin/bash

read -r -s PASSWD
echo "${PASSWD}" | /usr/local/bin/get_java_viewer -o /tmp/launch.jnlp "$@"
return_code="$?"
if [[ "${return_code}" -ne 0 ]]; then
    exit "${return_code}"
fi

# Replace variables in `/etc/supervisord.conf`
for v in XRES VNC_PASSWD; do
    eval sed -i "s/{$v}/\$$v/" /etc/supervisor/conf.d/supervisord.conf
done

# Install needed Java version
: ${JAVA_VERSION:=7u181}
pushd "/opt/java_packages/${JAVA_VERSION}" >/dev/null 2>&1 && \
dpkg -i *.deb && \
popd >/dev/null 2>&1 && \
pushd "/opt/icedtea" >/dev/null 2>&1 && \
dpkg -i *.deb && \
itweb-settings set deployment.security.level ALLOW_UNSIGNED
itweb-settings set deployment.security.jsse.hostmismatch.warning false
itweb-settings set deployment.manifest.attributes.check false
#itweb-settings set deployment.security.notinca.warning false

itweb-settings set deployment.security.expired.warning false
mkdir -p /root/.config/icedtea-web/security/
echo | openssl s_client -showcerts -servername ${KVM_HOSTNAME} -connect ${KVM_HOSTNAME}:443 2>/dev/null | openssl x509 -inform pem -outform pem > /root/cert.pem
keytool -importcert -noprompt -file /root/cert.pem -keystore /root/.config/icedtea-web/security/trusted.certs -storepass changeit
python /usr/local/bin/import_jnlp_cert.py
popd >/dev/null 2>&1

/usr/bin/supervisord
