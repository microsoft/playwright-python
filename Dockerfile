ARG base_version=python-3.7-buster
FROM domderen/playwright-python:$base_version
# 1. Install node12
RUN apt-get update && apt-get install -y curl && \
    curl -sL https://deb.nodesource.com/setup_12.x | bash - && \
    apt-get install -y nodejs

RUN apt-get install xauth -y
COPY . .
RUN pip install -r local-requirements.txt
RUN pip install -e .
RUN python build_driver.py
RUN python build_package.py
RUN pytest --timeout 90
