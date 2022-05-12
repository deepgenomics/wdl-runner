#!/usr/bin/python

# Copyright 2017 Google Inc.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

# file_util.py

import logging
import string
from pathlib import Path
from typing import List
from urllib.parse import urlparse

import simplejson
import sys_util
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from googleapiclient import discovery
from googleapiclient.errors import HttpError


def file_safe_substitute(file_name, mapping):
    """Performs placeholder replacement on a file, saving contents in place."""

    with open(file_name, "r") as f:
        file_contents = f.read()
        return string.Template(file_contents).safe_substitute(mapping)


def _upload_one_file(client: storage.Client, src_file: str, dest_gs_url: str):
    dest_parsed_url = urlparse(dest_gs_url)
    dest_bucketname = dest_parsed_url.hostname
    dest_bucket = client.bucket(dest_bucketname)
    src_parsed_url = urlparse(src_file)
    dest_parsed_url = urlparse(dest_gs_url)

    if src_parsed_url.scheme == "":  # local file upload

        def once():
            blob = dest_bucket.blob(
                str(
                    Path(
                        dest_parsed_url.path[1:],
                        Path(src_file).name,
                    )
                )
            )
            blob.upload_from_filename(src_file)

    elif src_parsed_url.scheme == "gs":  # copy between gcs buckets

        def once():
            src_bucketname = src_parsed_url.hostname
            src_bucket = client.bucket(src_bucketname)
            path = src_parsed_url.path
            src_blob = src_bucket.blob(path[1:])
            src_bucket.copy_blob(
                src_blob,
                dest_bucket,
                str(Path(dest_parsed_url.path[1:]) / Path(src_parsed_url.path).name),
            )

    else:
        raise ValueError(f"Cannot handle src file {src_file}")

    for attempt in range(3):
        try:
            logging.info(f"uploading file {src_file} to {dest_gs_url}")
            once()
        except GoogleCloudError as e:
            logging.warning(
                f"Copy {src_file} to {dest_gs_url} failed: attempt {attempt}", e
            )
        else:
            return

    raise RuntimeError(f"copying file {src_file} to {dest_gs_url} failed")


def gcs_cp(
    source_files: List[str],
    dest_gs_url: str,
    gs_client: storage.Client = storage.Client(),
):
    """
    Copies files between GCS buckets.

    Args:
        source_files: URLs of files to be copied, e.g
        ["gs://bucket1/some/path/file.txt", "gs://bucket1/some/path/file2.txt"]
        dest_gs_url: URL of destination folder, e.g gs://bucket2/other/path
    """
    for file in source_files:
        _upload_one_file(gs_client, file, dest_gs_url)


def verify_gcs_dir_empty_or_missing(path):
    """Verify that the output "directory" does not exist or is empty."""

    # Use the storage API directly instead of gsutil.
    # gsutil does not return explicit error codes and so to detect
    # a non-existent path would require capturing and parsing the error message.

    # Verify the input is a GCS path
    if not path.startswith("gs://"):
        sys_util.exit_with_error("Path is not a GCS path: '%s'" % path)

    # Tokenize the path into bucket and prefix
    parts = path[len("gs://") :].split("/", 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else None

    # Get the storage endpoint
    service = discovery.build("storage", "v1", cache_discovery=False)

    # Build the request - only need the name
    fields = "nextPageToken,items(name)"
    request = service.objects().list(
        bucket=bucket, prefix=prefix, fields=fields, maxResults=2
    )

    # If we get more than 1 item, we are done (directory not empty)
    # If we get zero items, we are done (directory empty)
    # If we get 1 item, then we need to check if it is a "directory object"

    items = []
    while request and len(items) < 2:
        try:
            response = request.execute()
        except HttpError as err:
            error = simplejson.loads(err.content)
            error = error["error"]

            sys_util.exit_with_error(
                "%s %s: '%s'" % (error["code"], error["message"], path)
            )

        items.extend(response.get("items", []))
        request = service.objects().list_next(request, response)

    if not items:
        return True

    if len(items) == 1 and items[0]["name"].rstrip("/") == prefix.rstrip("/"):
        return True

    return False


if __name__ == "__main__":
    pass
