#!/bin/bash

# Opt-in legacy AMI JViewer support (ephemeral child container only).
# ALLOW_LEGACY_AMI_JARS=true enables both ALLOW_LEGACY_JAR_SIGNATURES and ALLOW_INSECURE_JNLP_CERTS.
allow_legacy_jar_signatures() {
    local java_security="$1"
    if [[ -f "${java_security}" ]]; then
        sed -i '/^jdk\.jar\.disabledAlgorithms=/ s/MD5, //; s/, MD5//; s/ MD5//' "${java_security}"
    fi
}

legacy_jar_signatures_enabled() {
    [[ "${ALLOW_LEGACY_JAR_SIGNATURES:-false}" == "true" ]] || \
        [[ "${ALLOW_LEGACY_AMI_JARS:-false}" == "true" ]]
}

insecure_jnlp_certs_enabled() {
    [[ "${ALLOW_INSECURE_JNLP_CERTS:-false}" == "true" ]] || \
        [[ "${ALLOW_LEGACY_AMI_JARS:-false}" == "true" ]]
}

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
# Check if a Oracle Java version is requested
if [[ "${JAVA_VERSION%-oracle}" != "${JAVA_VERSION}" ]]; then
    JAVA_VERSION="${JAVA_VERSION%-oracle}"
    JAVA_MAJOR_VERSION="${JAVA_VERSION%%u*}"
    JAVA_PATCH_LEVEL="${JAVA_VERSION#*u}"
    ORACLE_JRE="/opt/oracle/jre1.${JAVA_MAJOR_VERSION}.0_${JAVA_PATCH_LEVEL}"
    mkdir -p /opt/oracle && \
    tar -C/opt/oracle/ -xvf "/opt/java_packages/${JAVA_VERSION}/jre-${JAVA_VERSION}-linux-x64.tar.gz" && \
    ln -s "/opt/oracle/jre1.${JAVA_MAJOR_VERSION}.0_${JAVA_PATCH_LEVEL}/bin/javaws" /usr/local/bin/javaws && \
    # Set the lowest possible security level
    # But first, call `import` to init the config directory structure (command will fail without X, but this is OK)
    javaws -import /tmp/launch.jnlp 2>/dev/null
    echo "deployment.security.level=MEDIUM" >> "/root/.java/deployment/deployment.properties" || return
    export PATH="/opt/oracle/jre1.${JAVA_MAJOR_VERSION}.0_${JAVA_PATCH_LEVEL}/bin:${PATH}"
    export JAVA_SECURITY_DIR="/root/.java/deployment/security"
    if legacy_jar_signatures_enabled; then
        allow_legacy_jar_signatures "${ORACLE_JRE}/lib/security/java.security"
    fi
else
    JAVA_VERSION="${JAVA_VERSION%-openjdk}"
    JAVA_MAJOR_VERSION="${JAVA_VERSION%%u*}"
    pushd "/opt/java_packages/${JAVA_VERSION}" >/dev/null 2>&1 && \
    dpkg -i *.deb && \
    popd >/dev/null 2>&1 && \
    pushd "/opt/icedtea" >/dev/null 2>&1 && \
    dpkg -i *.deb && \
    popd >/dev/null 2>&1
    itweb-settings set deployment.security.level ALLOW_UNSIGNED
    itweb-settings set deployment.security.jsse.hostmismatch.warning false
    if [[ "${JAVA_MAJOR_VERSION}" -eq 7 ]]; then
        itweb-settings set deployment.manifest.attributes.check false
    else
        itweb-settings set deployment.manifest.attributes.check NONE
    fi
    #itweb-settings set deployment.security.notinca.warning false
    itweb-settings set deployment.security.expired.warning false
    if insecure_jnlp_certs_enabled; then
        itweb-settings set deployment.security.itw.ignorecertissues true
    fi
    if legacy_jar_signatures_enabled; then
        allow_legacy_jar_signatures "/etc/java-${JAVA_MAJOR_VERSION}-openjdk/security/java.security"
    fi
    export JAVA_SECURITY_DIR="/root/.config/icedtea-web/security"
fi
mkdir -p "${JAVA_SECURITY_DIR}"
echo | openssl s_client -showcerts -servername ${KVM_HOSTNAME} -connect ${KVM_HOSTNAME}:443 2>/dev/null | openssl x509 -inform pem -outform pem > /root/cert.pem
keytool -importcert -noprompt -file /root/cert.pem -keystore "${JAVA_SECURITY_DIR}/trusted.certs" -storepass changeit
python /usr/local/bin/import_jnlp_cert.py

/usr/bin/supervisord
