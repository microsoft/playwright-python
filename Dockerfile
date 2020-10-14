FROM ubuntu:focal

# 1. Install latest Python
RUN apt-get update && apt-get install -y python3 python3-pip && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3 1

# 2. Install WebKit dependencies
RUN apt-get update && DEBIAN_FRONTEND="noninteractive" apt-get install -y --no-install-recommends \
    libwoff1 \
    libopus0 \
    libwebp6 \
    libwebpdemux2 \
    libenchant1c2a \
    libgudev-1.0-0 \
    libsecret-1-0 \
    libhyphen0 \
    libgdk-pixbuf2.0-0 \
    libegl1 \
    libnotify4 \
    libxslt1.1 \
    libevent-2.1-7 \
    libgles2 \
    libxcomposite1 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libepoxy0 \
    libgtk-3-0 \
    libharfbuzz-icu0

# 3. Install gstreamer and plugins to support video playback in WebKit.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgstreamer-gl1.0-0 \
    libgstreamer-plugins-bad1.0-0 \
    gstreamer1.0-plugins-good \
    gstreamer1.0-libav

# 4. Install Chromium dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libxss1 \
    libasound2 \
    fonts-noto-color-emoji \
    libxtst6

# 5. Install Firefox dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libdbus-glib-1-2 \
    libxt6

# 6. Install ffmpeg to bring in audio and video codecs necessary for playing videos in Firefox.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg

# 7. (Optional) Install XVFB if there's a need to run browsers in headful mode
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb

# 8. Feature-parity with node.js base images.
RUN apt-get update && apt-get install -y --no-install-recommends git ssh

# 9. Create the pwuser (we internally create a symlink for the pwuser and the root user)
RUN adduser pwuser

# === BAKE BROWSERS INTO IMAGE ===

# 1. Add tip-of-tree Playwright Python package to install its browsers.
#    The package should be built beforehand from tip-of-tree Playwright.
COPY ./dist/playwright*manylinux1*.whl /tmp/playwright-1.0-py3-none-manylinux1_x86_64.whl

# 2. Install playwright and then delete the installation.
#    Browsers will remain downloaded in `/home/pwuser/.cache/ms-playwright`.
RUN su pwuser -c "mkdir /tmp/pw && cd /tmp/pw && \
    pip install /tmp/playwright-1.0-py3-none-manylinux1_x86_64.whl && \
    python -m playwright install" && \
    rm -rf /tmp/pw && rm /tmp/playwright-1.0-py3-none-manylinux1_x86_64.whl

# 3. Symlink downloaded browsers for root user
RUN mkdir /root/.cache/ && \
    ln -s /home/pwuser/.cache/ms-playwright/ /root/.cache/ms-playwright
