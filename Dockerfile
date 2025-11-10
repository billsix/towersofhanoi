FROM registry.fedoraproject.org/fedora:43

COPY .tmux.conf /root/.tmux.conf

RUN dnf upgrade -y
RUN dnf install -y python3 \
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
