# Copyright 2021 Akamai Technologies, Inc. All Rights Reserved
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

"""
This module replaces the old test.bash script.

## Prep your environment for nose2

```bash
cd [cli-eaa-directory]
. ./venv/bin/activate
pip install nose nose2-html-report
```

## Tested with nose2
```bash
cd test
nose2 --html-report -v
open report.html
```
"""

import unittest
import subprocess
import shlex
import time
from pathlib import Path
import collections
import tempfile
import os

# Global variables
encoding = 'utf-8'


class CliEAATest(unittest.TestCase):
    testdir = None
    maindir = None

    def setUp(self):
        self.testdir = Path(__file__).resolve().parent
        self.maindir = Path(__file__).resolve().parent.parent

    def cli_command(self, *args):
        command = shlex.split(f'python3 {self.maindir}/bin/akamai-eaa')
        command.extend(*args)
        print("\nCOMMAND: ", command)
        return command

    def cli_run(self, *args):
        cmd = subprocess.Popen(self.cli_command(str(a) for a in args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return cmd

    def line_count(filename):
        count = 0
        with open(filename) as f:
            while next(f, False):
                count += 1
        return count

    def duplicate_count(filename):
        total_count = 0
        with open(filename) as infile:
            counts = collections.Counter(l.strip() for l in infile)
        for line, count in counts.most_common():
            if count > 1:
                print(f"DUPLICATE[{count}] {line}")
                total_count += 1
        return total_count


class TestEvents(CliEAATest):

    after = int(time.time() - 15 * 60)
    before = int(time.time())

    def test_useraccess_log(self):
        """
        Fetch User Access log events
        """
        cmd = self.cli_run("log", "access", "--start", self.after, "--end", self.before)
        stdout, stderr = cmd.communicate(timeout=60)
        events = stdout.decode(encoding)
        event_count = len(events.splitlines())
        self.assertGreater(event_count, 0, "We expect at least one user access event")
        self.assertEqual(cmd.returncode, 0, 'return code must be 0')


class TestCliEAA(CliEAATest):

    def test_no_edgerc(self):
        """
        Call CLI with a bogus edgerc file, help should be displayed.
        """
        cmd = self.cli_run('-e', 'file_not_exist')
        stdout, stderr = cmd.communicate()
        output = stdout.decode(encoding)
        self.assertIn("usage: akamai eaa", output)
        # self.assertEqual(cmd.returncode, 0, 'return code must be 0')

    def test_cli_version(self):
        """
        Ensure version of the CLI is displayed
        """
        cmd = self.cli_run('version')
        stdout, stderr = cmd.communicate()
        self.assertRegex(stdout.decode(encoding), r'[0-9]+\.[0-9]+\.[0-9]+\n', 'Version should be x.y.z')
        self.assertEqual(cmd.returncode, 0, 'return code must be 0')


if __name__ == '__main__':
    unittest.main()
