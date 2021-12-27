FROM python:3.9-alpine

COPY . /opt/venv/xdcc-pipe
RUN pip3 --no-cache-dir install /opt/venv/xdcc-pipe

RUN adduser -D xdcc-pipe
USER xdcc-pipe

ENTRYPOINT ["/usr/local/bin/xdcc-pipe"]
