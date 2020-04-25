#!/usr/bin/env python

import os

from pyquery import PyQuery as pq
import requests

java_security_dir = os.environ["JAVA_SECURITY_DIR"]

xml = pq(filename="/tmp/launch.jnlp")

codebase = xml[0].attrib["codebase"]
n = 1
for jar in xml.find("resources > jar"):
    pack_enabled = False
    version_enabled = False
    props = pq(jar.getparent()).find("property")
    for prop in props:
        if prop.get("name") == "jnlp.packEnabled" and prop.get("value") == "true":
            pack_enabled = True
        elif prop.get("name") == "jnlp.versionEnabled" and prop.get("value") == "true" and "version" in jar.attrib:
            version_enabled = True

    if version_enabled:
        url = codebase + "/" + jar.attrib["href"][:-4] + "__V" + jar.attrib["version"] + ".jar"
    else:
        url = codebase + "/" + jar.attrib["href"]
    if pack_enabled:
        url = url + ".pack.gz"
    print("Found jar: " + url)

    contents = requests.get(url, verify=False)
    add_ext = "" if not pack_enabled else ".pack.gz"

    with open("/tmp/jnlp_certs_{}.jar{}".format(n, add_ext), "wb") as f:
        f.write(contents.content)
    if pack_enabled:
        os.system("unpack200 /tmp/jnlp_certs_{}.jar.pack.gz /tmp/jnlp_certs_{}.jar".format(n, n))

    os.system("bash -c 'keytool -printcert -jarfile /tmp/jnlp_certs_{}.jar -rfc > /tmp/jnlp_certs_{}.pem'".format(n, n))
    os.system(
        "keytool -importcert -noprompt -file /tmp/jnlp_certs_{}.pem -keystore {}/trusted.certs -alias jnlp_certs_{} -storepass changeit".format(
            n, java_security_dir, n
        )
    )
    n += 1
