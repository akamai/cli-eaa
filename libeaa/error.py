# Copyright 2024 Akamai Technologies, Inc. All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from enum import Enum
from unittest.signals import installHandler

class rc_error(Enum):
    """
    Command line return codes from 0 (all good) to 255
    """
    OK = 0
    GENERAL_ERROR = 2
    EDGERC_MISSING = 30
    EDGERC_SECTION_NOT_FOUND = 31
    ERROR_NOT_SPECIFIED = 255


def cli_exit_with_error(error_code, message=None):
    """
    Exit the command line with error_code (integer or rc_error) with an optional message.
    """
    if message:
        sys.stderr.write(message)
    if isinstance(error_code, rc_error):
        sys.exit(error_code.value)
    elif isinstance(error_code, int):
        sys.exit(error_code)
    else:
        sys.exit(rc_error.ERROR_NOT_SPECIFIED.value)