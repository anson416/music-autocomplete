ARG arch
FROM --platform=linux/${arch} python:3.10-slim

WORKDIR /api
COPY . /api

RUN apt-get update -qq && \
    apt-get install --no-install-recommends -qq -y \
        libfluidsynth3 \
        fluid-soundfont-gm \
        build-essential \
        libasound2-dev \
        libjack-dev \
        ffmpeg \
        sox \
        git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    python3 -m pip install --no-cache-dir -qU pip setuptools wheel && \
    python3 -m pip install --no-cache-dir -r requirements.txt && \
    python3 -m pip install --no-deps --no-cache-dir magenta && \
    cd mustrans && \
    git clone --branch=main https://github.com/magenta/mt3 && \
    cd mt3 && \
    python3 -m pip install -e . && \
    cd ../.. && \
    python3 -m pip cache purge

# ARG arch
# RUN if [ ${arch} = "arm64" ]; then \
#         ln -s /usr/lib/aarch64-linux-gnu/libfluidsynth.so.3 /usr/lib/aarch64-linux-gnu/libfluidsynth.so.1; \
#     else \
#         ln -s /usr/lib/x86_64-linux-gnu/libfluidsynth.so.3 /usr/lib/x86_64-linux-gnu/libfluidsynth.so.1; \
#     fi

ENTRYPOINT [ "python3", "main.py" ]
# ENTRYPOINT [ "/bin/bash" ]
