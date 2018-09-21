FROM debian:jessie
LABEL maintainer="Ingo Heimbach <i.heimbach@fz-juelich.de>"

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates tar net-tools xvfb x11vnc supervisor fluxbox openjdk-7-jre icedtea-7-plugin python-numpy python-pip python-wheel && \
    pip install future requests websockify && \
    rm -rf /var/lib/apt/lists/*

RUN curl -o /tmp/novnc.tar.gz  -L https://github.com/novnc/noVNC/archive/v1.0.0.tar.gz && \
    tar -xvf /tmp/novnc.tar.gz -C /opt/ && \
    ln -s /opt/noVNC-1.0.0/utils/launch.sh /usr/local/bin/launch_novnc && \
    rm -f /tmp/novnc.tar.gz

COPY entrypoint.sh /usr/local/bin/docker-entrypoint
COPY get_java_viewer.py /usr/local/bin/get_java_viewer
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

WORKDIR /root/

ENV DISPLAY :0
EXPOSE 8080

ENTRYPOINT ["/usr/local/bin/docker-entrypoint"]
