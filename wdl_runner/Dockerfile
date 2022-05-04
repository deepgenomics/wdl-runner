# Copyright 2017 Google Inc.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

FROM gcr.io/google.com/cloudsdktool/cloud-sdk:alpine

# Install openjdk11 and pip
RUN apk add --no-cache openjdk11-jre py-pip

COPY requirements.frozen /
RUN pip3 install -r /requirements.frozen && rm /requirements.frozen

# Remove pip
RUN python3 -m pip uninstall pip --yes

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
