# Copyright 2017 Google Inc.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

FROM python:3.11-slim as compiler
ENV PYTHONUNBUFFERED 1

WORKDIR /app/

RUN python -m venv /opt/venv
# Enable venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.frozen /app/requirements.frozen
RUN pip install -r requirements.frozen
# change symlink to match the cloud-sdk image
RUN rm /opt/venv/bin/python && ln -s /usr/bin/python /opt/venv/bin/python

FROM gcr.io/google.com/cloudsdktool/cloud-sdk:472.0.0-alpine

# Install openjdk11 and pip
RUN apk add --no-cache openjdk11-jre py-pip

# Copy the wdl_runner python, shell script, and dependencies
RUN mkdir /wdl_runner
COPY cromwell_driver.py \
     file_util.py \
     sys_util.py \
     wdl_outputs_util.py \
     wdl_runner.py \
     wdl_runner.sh \
     /wdl_runner/
RUN chmod u+x /wdl_runner/wdl_runner.sh

# Copy Cromwell and the Cromwell conf template
RUN mkdir /cromwell
RUN cd /cromwell && \
    curl -L -O https://github.com/broadinstitute/cromwell/releases/download/69/cromwell-69.jar
RUN ln /cromwell/cromwell-69.jar /cromwell/cromwell.jar
COPY jes_template.conf /cromwell/

# Set up the runtime environment
ENV CROMWELL /cromwell/cromwell.jar
ENV CROMWELL_CONF /cromwell/jes_template.conf

WORKDIR /wdl_runner

COPY --from=compiler /opt/venv /opt/venv
# Enable venv
ENV PATH="/opt/venv/bin:$PATH"
