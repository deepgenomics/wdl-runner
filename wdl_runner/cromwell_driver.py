#!/usr/bin/python

# Copyright 2017 Google Inc.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

# cromwell_driver.py
#
# This script provides a library interface to Cromwell, namely:
#  * Start the Cromwell server
#  * Submit execution requests to Cromwell
#  * Poll Cromwell for job status

import base64
import logging
import os
import subprocess
import time
from typing import List

import requests


class CromwellDriver(object):
    def __init__(self, cromwell_conf, cromwell_jar, jvm_flags: List[str] = None):
        self.cromwell_conf = cromwell_conf
        self.cromwell_jar = cromwell_jar
        self.jvm_flags = jvm_flags

        self.cromwell_proc = None

    def start(self):
        """Start the Cromwell service."""
        if self.cromwell_proc:
            logging.info("Request to start Cromwell: already running")
            return

        jvm_args = ["-Dconfig.file=" + self.cromwell_conf]
        if self.jvm_flags is not None:
            jvm_args += self.jvm_flags
        jvm_args += ["-jar", self.cromwell_jar]
        cmd = ["java"] + jvm_args + ["server"]
        self.cromwell_proc = subprocess.Popen(cmd)

        logging.info("Started Cromwell using command: %s", "'" + " ".join(cmd) + "'")

    def fetch(self, wf_id=None, post=False, files=None, method=None):
        url = "http://localhost:8000/api/workflows/v1"
        if wf_id is not None:
            url = os.path.join(url, wf_id)
        if method is not None:
            url = os.path.join(url, method)
        if post:
            logging.info("send POST request to Cromwell server: %s with files %s", url,
                         ", ".join(files))
            r = requests.post(url, files=files)
        else:
            logging.info("send GET request to Cromwell server: %s", url)
            r = requests.get(url)
        logging.info("Response: %s", r.json())
        return r.json()

    def submit(
        self,
        wdl,
        workflow_inputs,
        workflow_options,
        workflow_dependencies,
        sleep_time=15,
    ):
        """Post new job to the server and poll for completion."""

        # Add required input files
        with open(wdl, "rb") as f:
            wf_source = f.read()
        with open(workflow_inputs, "rb") as f:
            wf_inputs = f.read()

        files = {
            "workflowSource": wf_source,
            "workflowInputs": wf_inputs,
        }

        if workflow_dependencies:
            with open(workflow_dependencies, "rb") as f:
                # Read as Base64 byte string
                wf_dependencies = f.read()
                # Convert to binary zip file
                files["workflowDependencies"] = base64.decodebytes(wf_dependencies)

        # Add workflow options if specified
        if workflow_options:
            with open(workflow_options, "rb") as f:
                wf_options = f.read()
                files["workflowOptions"] = wf_options

        # After Cromwell start, it may take a few seconds to be ready for requests.
        # Poll up to a minute for successful connect and submit.

        job = None
        max_time_wait = 60
        wait_interval = 5

        time.sleep(wait_interval)
        for attempt in range(max_time_wait // wait_interval):
            try:
                job = self.fetch(post=True, files=files)
                break
            except requests.exceptions.ConnectionError as e:
                logging.info(
                    "Failed to connect to Cromwell (attempt %d of %d): %s",
                    attempt + 1, max_time_wait // wait_interval, e
                )
                logging.info("Sleep for %d seconds before next attempt", wait_interval)
                time.sleep(wait_interval)

        if not job:
            raise TimeoutError(
                "Failed to connect to Cromwell after {0} seconds".format(max_time_wait)
            )

        if job["status"] != "Submitted":
            raise RuntimeError(
                "Job status from Cromwell was not 'Submitted', instead '{0}'".format(
                    job["status"]
                )
            )

        # Job is running.
        cromwell_id = job["id"]
        logging.info("Job submitted to Cromwell. job id: %s", cromwell_id)

        # Poll Cromwell for job completion.
        attempt = 0
        max_failed_attempts = 3
        while True:
            time.sleep(sleep_time)

            # Cromwell occasionally fails to respond to the status request.
            # Only give up after 3 consecutive failed requests.
            try:
                logging.info("get ID: %s job status from Cromwell", cromwell_id)
                status_json = self.fetch(wf_id=cromwell_id, method="status")
                attempt = 0
            except requests.exceptions.ConnectionError as e:
                attempt += 1
                logging.info(
                    "Error polling Cromwell job status (attempt %d of %d): %s",
                    attempt, max_failed_attempts, e
                )

                if attempt >= max_failed_attempts:
                    raise TimeoutError(
                        "Cromwell did not respond for %d consecutive requests" % attempt
                        )
                continue

            status = status_json["status"]
            if status == "Succeeded":
                break
            elif status == "Submitted":
                pass
            elif status == "Running":
                pass
            else:
                raise RuntimeError(
                    "Status of job is not Submitted, Running, or Succeeded: %s" % status
                )

        logging.info("Cromwell job status: %s", status)

        # Cromwell produces a list of outputs and full job details
        outputs = self.fetch(wf_id=cromwell_id, method="outputs")
        metadata = self.fetch(wf_id=cromwell_id, method="metadata")

        return outputs, metadata


if __name__ == "__main__":
    pass
