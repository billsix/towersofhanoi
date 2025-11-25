FROM registry.fedoraproject.org/fedora:43

COPY .tmux.conf /root/.tmux.conf

RUN  --mount=type=cache,target=/var/cache/libdnf5 \
     --mount=type=cache,target=/var/lib/dnf \
     echo "keepcache=True" >> /etc/dnf/dnf.conf && \
     dnf upgrade -y
RUN  --mount=type=cache,target=/var/cache/libdnf5 \
     --mount=type=cache,target=/var/lib/dnf \
     echo "keepcache=True" >> /etc/dnf/dnf.conf && \
     dnf install -y clear \
                   python3 \
                   python3-pip \
                   tmux \
                   nano \
		   ruff \
		   python3-isort \
		   python3-pysnooper \
		   python3-pytest \
                   python3-termcolor

COPY entrypoint/.bashrc /root/
COPY entrypoint/format.sh /

RUN echo "export PS1='>'" >> ~/.bashrc

ENTRYPOINT ["/entrypoint.sh"]
