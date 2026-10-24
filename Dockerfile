FROM registry.fedoraproject.org/fedora:44

# Root image of hanoi: the BOOK layer (Sphinx + TeX Live) after the per-language split.
# The language toolchains moved to the self-contained subprojects (python/ and rust/,
# each with its own Dockerfile/Makefile). This image builds the Sphinx book, which needs
# Python 3 + the hanoigame package (for the by-hand page generator / drift guard) and the
# docs toolchain.

ARG BUILD_DOCS=0

# System-package installation lives in per-group scripts (entrypoint/0N-install-*.sh),
# host-runnable with no container runtime; WHICH optional groups run is decided here by
# the ARG `if` blocks. The dnf cache mount + keepcache stay in the Dockerfile.
# 01-install-base.sh also does `dnf upgrade`.
COPY entrypoint/01-install-base.sh entrypoint/02-install-docs.sh /usr/local/bin/

RUN  --mount=type=cache,target=/var/cache/libdnf5 \
     --mount=type=cache,target=/var/lib/dnf \
     echo "keepcache=True" >> /etc/dnf/dnf.conf && \
     /usr/local/bin/01-install-base.sh && \
     if [ "$BUILD_DOCS" = "1" ]; then /usr/local/bin/02-install-docs.sh; fi && \
     echo "make docs" >> ~/.bash_history

# The book pulls code listings from python/src and runs the hanoigame package / the
# by-hand generator, so install the Python deps (wxPython from dnf, so strip it here).
COPY python/requirements.txt /requirements.txt
RUN  --mount=type=cache,target=/root/.cache/uv \
     uv pip install --system setuptools && \
     grep -v -i wxpython /requirements.txt > /requirements-nowx.txt && \
     uv pip install --system -r /requirements-nowx.txt && \
     rm /requirements.txt /requirements-nowx.txt

COPY entrypoint/.bashrc /root/
COPY entrypoint/entrypoint.sh /entrypoint.sh
COPY entrypoint/format.sh /format.sh
COPY entrypoint/type-check.sh /type-check.sh

RUN echo "export PS1='>'" >> ~/.bashrc

ENTRYPOINT ["/entrypoint.sh"]
