FROM registry.fedoraproject.org/fedora:43

ARG BUILD_DOCS=0

RUN  --mount=type=cache,target=/var/cache/libdnf5 \
     --mount=type=cache,target=/var/lib/dnf \
     echo "keepcache=True" >> /etc/dnf/dnf.conf && \
     dnf upgrade -y
RUN  --mount=type=cache,target=/var/cache/libdnf5 \
     --mount=type=cache,target=/var/lib/dnf \
     echo "keepcache=True" >> /etc/dnf/dnf.conf && \
     dnf install -y clear \
                   python3 \
                   tmux \
                   nano \
		   ruff \
		   python3-isort \
		   python3-pysnooper \
		   python3-pytest \
                   python3-termcolor \
                   uv \
                   ty ; \
    if [ "$BUILD_DOCS" = "1" ]; then \
       dnf install -y \
                   aspell \
                   aspell-en \
                   latexmk \
                   make \
                   mathjax \
                   mathjax-main-fonts \
                   mathjax-math-fonts \
                   python3-furo \
                   python3-sphinx-latex \
                   python3-sphinx_rtd_theme \
                   texlive \
                   texlive-anyfontsize \
                   texlive-dvipng \
                   texlive-dvisvgm \
                   texlive-standalone; \
    fi ;


COPY python/requirements.txt /requirements.txt
RUN  uv pip install --system setuptools && \
     uv pip install --system -r /requirements.txt && \
     rm /requirements.txt

COPY entrypoint/.bashrc /root/
COPY entrypoint/entrypoint.sh /entrypoint.sh
COPY entrypoint/format.sh /

RUN echo "export PS1='>'" >> ~/.bashrc

ENTRYPOINT ["/entrypoint.sh"]
