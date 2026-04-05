FROM python@sha256:7026274c107626d7e940e0e5d6730481a4600ae95d5ca7eb532dd4180313fea9

RUN apt update && apt upgrade && apt install -y ffmpeg && \
	apt-get clean && rm -rf /var/lib/apt/lists/*

RUN useradd --uid 1001 --shell /bin/bash user --create-home


WORKDIR /app

COPY requirements.txt requirements.txt
RUN python -m pip install -r requirements.txt --no-cache-dir
COPY . .
RUN chmod -R a+rwx ./* 
USER user
ENTRYPOINT [ "/bin/sh", "run.sh" ]
