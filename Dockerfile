FROM python@sha256:7026274c107626d7e940e0e5d6730481a4600ae95d5ca7eb532dd4180313fea9

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN useradd --uid 1001 --shell /bin/bash user --create-home


WORKDIR /app

COPY requirements.txt requirements.txt
RUN python -m pip install -r requirements.txt --no-cache-dir
COPY --chown=user:user . .

RUN install -d -o user -g user /app/static \
    && touch /app/history \
    && chown -R user:user /app

EXPOSE 5000

USER user
ENTRYPOINT [ "/bin/sh", "run.sh" ]
