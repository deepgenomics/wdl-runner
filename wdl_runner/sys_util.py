#!/usr/bin/python

# Copyright 2017 Google Inc.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

# sys_util.py

import logging
import os
from typing import Dict


def copy_from_env(env_vars, environ) -> Dict[str, str]:
  """Returns a dict of required environment variables."""

  result = {}
  for e in env_vars:
    val = environ.get(e, None)
    if val is None:
      raise RuntimeError("the " + e + " environment variable must be set")
    logging.info(e + "->" + os.environ[e])
    result[e] = val

  return result


if __name__ == '__main__':
  pass
