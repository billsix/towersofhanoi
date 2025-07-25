FROM docker.io/debian:trixie

COPY .tmux.conf /root/.tmux.conf

RUN apt update  && apt upgrade -y
RUN apt install    -y python3-full \
                      python3-pip \
                      tmux \
                      nano

RUN echo "alias ls='ls --color=auto'" >> ~/.bashrc


ENTRYPOINT ["/entrypoint.sh"]
