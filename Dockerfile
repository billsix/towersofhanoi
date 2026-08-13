FROM registry.fedoraproject.org/fedora:44

ARG BUILD_DOCS=0

# System-package installation lives in per-group scripts (entrypoint/0N-install-*.sh),
# host-runnable with no container runtime; the scripts take no options -- WHICH optional
# groups run is decided here by the ARG `if` blocks. The dnf cache mount + keepcache stay
# in the Dockerfile (build plumbing). 01-install-base.sh also does `dnf upgrade`.
COPY entrypoint/01-install-base.sh entrypoint/02-install-docs.sh /usr/local/bin/

RUN  --mount=type=cache,target=/var/cache/libdnf5 \
     --mount=type=cache,target=/var/lib/dnf \
     echo "keepcache=True" >> /etc/dnf/dnf.conf && \
     /usr/local/bin/01-install-base.sh && \
     if [ "$BUILD_DOCS" = "1" ]; then /usr/local/bin/02-install-docs.sh; fi && \
     echo "hanoi" >> ~/.bash_history


COPY python/requirements.txt /requirements.txt
RUN  uv pip install --system setuptools && \
     grep -v -i wxpython /requirements.txt > /requirements-nowx.txt && \
     uv pip install --system -r /requirements-nowx.txt && \
     rm /requirements.txt /requirements-nowx.txt

COPY entrypoint/.bashrc /root/
COPY entrypoint/entrypoint.sh /entrypoint.sh
COPY entrypoint/format.sh /

RUN echo "export PS1='>'" >> ~/.bashrc

ENTRYPOINT ["/entrypoint.sh"]
