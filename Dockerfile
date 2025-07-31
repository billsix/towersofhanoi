FROM registry.fedoraproject.org/fedora:42

COPY .tmux.conf /root/.tmux.conf

RUN dnf upgrade -y
RUN dnf install -y python3 \
                   python3-pip \
                   tmux \
                   nano \
		   ruff \
		   python3-isort \
		   python3-pysnooper \
		   python3-pytest


ENTRYPOINT ["/entrypoint.sh"]
