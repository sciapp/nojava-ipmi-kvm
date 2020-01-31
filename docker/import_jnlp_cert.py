#!/usr/bin/env python

import os

from pyquery import PyQuery as pq
import requests

xml = pq(filename='/tmp/launch.jnlp')

codebase = xml[0].attrib['codebase']
n = 1
for jar in xml.find('resources > jar'):
    url = codebase + '/' + jar.attrib['href']
    print('Found jar: ' + url)

    contents = requests.get(url, verify=False)
    with open('/tmp/jnlp_certs_{}.jar'.format(n), 'wb') as f:
        f.write(contents.content)

    os.system(
        "bash -c 'keytool -printcert -jarfile /tmp/jnlp_certs_{}.jar -rfc > /tmp/jnlp_certs_{}.pem'"
        .format(n, n)
    )
    os.system(
        'keytool -importcert -noprompt -file /tmp/jnlp_certs_{}.pem -keystore /root/.config/icedtea-web/security/trusted.certs -alias jnlp_certs_{} -storepass changeit'
        .format(n, n)
    )
    n += 1
