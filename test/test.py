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

"""
This module replaces the old test.bash script.

Test with nose2
---------------

Prep your environment for nose2

.. code-block:: bash
   cd [cli-eaa-directory]
   . ./venv/bin/activate # or any other location/preference
   pip install nose nose2-html-report

Run all tests

.. code-block:: bash
   cd test
   nose2 --html-report -v
   open report.html

Test with pytest-html
---------------------

See also https://pytest-html.readthedocs.io/en/latest/

.. code-block:: bash
   pip install pytest-html
   cd test
   # Specify the test app URL to generate traffic against
   URL_TEST_TRAFFIC=https://login:password@myclassicapp.go.akamai-access.com pytest --html=report.html --self-contained-html test.py
   # test a specific test fixture
   pytest --html=report.html --self-contained-html -k test_connector_health_tail test.py

"""

# Python builtin modules
import unittest
import subprocess
import shlex
import time
from pathlib import Path
import collections
import os
import json
import re
import signal

# CLI EAA
from libeaa.error import rc_error

# 3rd party modules
import requests

# Global variables
encoding = 'utf-8'

def pytest_html_report_title(report):
    report.title = "Akamai cli-eaa"

class CliEAATest(unittest.TestCase):
    testdir = None
    maindir = None

    def setUp(self):
        self.testdir = Path(__file__).resolve().parent
        self.maindir = Path(__file__).resolve().parent.parent
        edgerc = CliEAATest.config_edgerc()
        if not os.path.isfile(edgerc):
            self.fail(f'EdgeRC file {edgerc} doesn\'t exist.')

    def cli_command(self, *args):
        command = shlex.split(f'python3 {self.maindir}/bin/akamai-eaa')
        section = CliEAATest.config_section()
        # Core CLI arguments goes first
        if '--section' not in args and section:
            command.append('--section')
            command.append(section)
        edgerc = CliEAATest.config_edgerc()
        if '--edgerc' not in args and section:
            command.append('--edgerc')
            command.append(edgerc)
        # Then CLI-EAA arguments
        command.extend(*args)
        CliEAATest.cli_print("\nSHELL COMMAND: ", shlex.join(command))
        return command

    def cli_run(self, *args):
        cmd = subprocess.Popen(self.cli_command(str(a) for a in args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return cmd

    def cli_print(*s):
        print("cli-eaa>", *s)

    def url_safe_print(url):
        """
        Securely print the output of a URL that may have authentication credentials.
        """
        pattern = re.compile(r'(\b(?:[a-z]{,5})://.*:)(.*)(@[^ \b]+)', re.MULTILINE)
        result = re.sub(pattern, "\\1********\\3", url)
        return result

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
                CliEAATest.cli_print(f"DUPLICATE[{count}] {line}")
                total_count += 1
        return total_count

    def config_section():
        return os.getenv('SECTION', 'default')

    def config_edgerc():
        return os.getenv('EDGERC', os.path.expanduser("~/.edgerc"))

class TestEvents(CliEAATest):

    after = int(time.time() - 15 * 60) # 15 minutes by default
    before = int(time.time())

    @classmethod
    def setUpClass(cls):
        url = os.getenv('URL_TEST_TRAFFIC')
        if url:
            cls.after = int(time.time())
            cls.config_testapp_url()
            cls.before = int(time.time())
        else:
            span = os.getenv('URL_SCAN_SPAN')
            if span:
                cls.after = int(time.time() - int(span))
                cls.before = int(time.time())

    @classmethod
    def config_testapp_url(cls):
        """
        Generate some traffic against a webapp defined
        """
        delay = 60
        url = os.getenv('URL_TEST_TRAFFIC')
        if url:
            CliEAATest.cli_print(f"Test fingerprint: {id(cls):x}")
            CliEAATest.cli_print("Generating some traffic against base URL_TEST_TRAFFIC={urle}...".format(urle=CliEAATest.url_safe_print(url)))
            for i in range(0, 10):
                resp = requests.get(url, params={'__unittest_fp': f"{id(cls):x}", '__unittest_seq': i})
                CliEAATest.cli_print(f"{i}:", CliEAATest.url_safe_print(resp.url), resp)
                # time.sleep(0.3)
            CliEAATest.cli_print(f"Now waiting {delay}s to get the log collected")
            time.sleep(delay)
        else:
            CliEAATest.cli_print("WARNING: no environment variable URL_TEST_TRAFFIC defined, we assume "
                                 "the traffic is generated separately. You may use URL_SCAN_SPAN to "
                                 "configure how far back we need to scan in the past.")

    def test_useraccess_log_raw(self):
        """
        Fetch User Access log events (RAW format)
        """
        self.assertNotEqual(os.environ.get('URL_TEST_TRAFFIC'), "", "set URL_TEST_TRAFFIC env for this test")
        cmd = self.cli_run("log", "access", "--start", self.after, "--end", self.before)
        stdout, stderr = cmd.communicate(timeout=60)
        events = stdout.decode(encoding)
        event_count = len(events.splitlines())
        self.assertGreater(event_count, 0, "We expect at least one user access event, set URL_TEST_TRAFFIC env")
        self.assertEqual(cmd.returncode, 0, 'return code must be 0')

    def test_useraccess_log_raw_v2(self):
        """
        Fetch User Access log events (RAW format) using the API v2 introduced in EAA 2021.02
        """
        self.assertNotEqual(os.environ.get('URL_TEST_TRAFFIC'), "", "set URL_TEST_TRAFFIC env for this test")
        cmd = self.cli_run("log", "access", "--start", self.after, "--end", self.before)
        stdout, stderr = cmd.communicate(timeout=60)
        events = stdout.decode(encoding)
        event_count = len(events.splitlines())
        self.assertGreater(event_count, 0, "We expect at least one user access event")
        self.assertEqual(cmd.returncode, 0, 'return code must be 0')

    def test_admin_log_raw(self):
        """
        Fetch Admin log events (RAW format)
        Command line: akamai eaa log admin
        """
        # We override the default after variable
        # because admin event are not triggered often
        # We use two weeks as baseline
        # TODO: create a test that trigger and admin event and then test
        after = int(time.time() - 14 * 24 * 60 * 60)
        cmd = self.cli_run("log", "admin", "--start", after, "--end", self.before)
        stdout, stderr = cmd.communicate(timeout=60)
        events = stdout.decode(encoding)
        event_count = len(events.splitlines())
        self.assertGreater(event_count, 0, "We expect at least one admin event")
        self.assertEqual(cmd.returncode, 0, 'return code must be 0')


    def test_useraccess_log_json(self):
        """
        Fetch User Access log events (JSON format)
        """
        cmd = self.cli_run("log", "access", "--start", self.after, "--end", self.before, "--json")
        stdout, stderr = cmd.communicate(timeout=60)
        events = stdout.decode(encoding)
        CliEAATest.cli_print(events)
        event_count = len(events.splitlines())
        self.assertGreater(event_count, 0, "We expect at least one user access event")
        self.assertEqual(cmd.returncode, 0, 'return code must be 0')


    def test_useraccess_log_json_v2(self):
        """
        Fetch User Access log events (JSON format)
        """
        cmd = self.cli_run("log", "access", "--start", self.after, "--end", self.before, "--json")
        stdout, stderr = cmd.communicate(timeout=60)
        scanned_events = stdout.decode(encoding)
        lines = scanned_events.splitlines()
        for l in lines:
            event = json.loads(l)
            CliEAATest.cli_print(json.dumps(event, indent=2))
        
        event_count = len(lines)
        self.assertGreater(event_count, 0, "We expect at least one user access event")
        self.assertEqual(cmd.returncode, 0, 'return code must be 0')

class TestApplication(CliEAATest):

    def test_search(self):
        """
        Search for all applications in the account
        """
        cmd = self.cli_run('search')
        stdout, stderr = cmd.communicate()
        output = stdout.decode(encoding)
        app_count = len(output.splitlines())
        self.assertGreater(app_count, 0, "We expect at least one application to be configured")
        self.assertEqual(cmd.returncode, 0, 'return code must be 0')


class TestConnectors(CliEAATest):

    def assert_list_connectors(self, con_count, cmd):
        self.assertGreater(con_count, 0, "We expect at least one connector to be configured")
        self.assertEqual(cmd.returncode, 0, 'return code must be 0')


    def test_list_connectors(self):
        """
        List all connectors in the account (RAW)
        Command line: akamai eaa c
        """
        cmd = self.cli_run('c')
        stdout, stderr = cmd.communicate()
        output = stdout.decode(encoding)
        con_count = len(output.splitlines())
        self.assert_list_connectors(con_count, cmd)

    def test_list_connectors_json(self):
        """
        List all connectors in the account (JSON)
        Command line: akamai eaa c --json
        """
        cmd = self.cli_run('c', 'list', '--json')
        stdout, stderr = cmd.communicate()
        output = stdout.decode(encoding)
        con_count = len(output.splitlines())
        self.assert_list_connectors(con_count, cmd)

    def test_connector_health_raw(self):
        """
        Run connector command to fetch full health statuses.
        """
        cmd = self.cli_run('c', 'list', '--perf')
        stdout, stderr = cmd.communicate()
        output = stdout.decode(encoding)
        con_count = len(output.splitlines())
        self.assert_list_connectors(con_count, cmd)

    def test_connector_health_json(self):
        """
        Run connector command to fetch full health statuses (JSON version).
        """
        cmd = self.cli_run('c', 'list', '--json', '--perf')
        stdout, stderr = cmd.communicate()
        output = stdout.decode(encoding)
        con_count = len(output.splitlines())
        self.assert_list_connectors(con_count, cmd)

    def test_connector_health_tail(self):
        """
        Run connector command to fetch full health statuses in follow mode
        We use the RAW format for convenience (easier to read in the output)
        """
        cmd = self.cli_run('-d', '-v', 'c', 'list', '--perf', '--tail', '-i', '5')
        time.sleep(60)  # Long enough to collect some data
        cmd.send_signal(signal.SIGINT)
        stdout, stderr = cmd.communicate(timeout=50.0)
        CliEAATest.cli_print("rc: ", cmd.returncode)
        for l in stdout.splitlines():
            CliEAATest.cli_print("stdout>", l)
        for l in stderr.splitlines():
            CliEAATest.cli_print("stderr>", l)
        self.assertGreater(len(stdout), 0, "No connector health output")

    def test_connector_allowlist_ipcidr(self):
        cmd = self.cli_run('-d', '-v', 'c', 'allowlist')
        stdout, stderr = cmd.communicate(timeout=50.0)
        for l in stdout.splitlines():
            CliEAATest.cli_print("stdout>", l)
        for l in stderr.splitlines():
            CliEAATest.cli_print("stderr>", l)
        self.assertGreater(len(stdout), 0, "No allowlist IP/CIDR output")

    def test_connector_allowlist_fqdn(self):
        cmd = self.cli_run('-d', '-v', 'c', 'allowlist', '--fqdn')
        stdout, stderr = cmd.communicate(timeout=50.0)
        for l in stdout.splitlines():
            CliEAATest.cli_print("stdout>", l)
        for l in stderr.splitlines():
            CliEAATest.cli_print("stderr>", l)
        self.assertGreater(len(stdout), 0, "No allowlist hostname output")

    def test_connector_allowlist_sincetime(self):
        cmd = self.cli_run('-d', '-v', 'c', 'allowlist', '--since-time', '2000-01-01T00:00:00.0000000Z')
        stdout, stderr = cmd.communicate(timeout=50.0)
        for l in stdout.splitlines():
            CliEAATest.cli_print("stdout>", l)
        for l in stderr.splitlines():
            CliEAATest.cli_print("stderr>", l)
        self.assertGreater(len(stdout), 0, "No allowlist IP/CIDR output with change set before Jan 1, 2000")

class TestIdentity(CliEAATest):

    def test_list_directories(self):
        cmd = self.cli_run('dir', 'list')
        stdout, stderr = cmd.communicate()
        output = stdout.decode(encoding)
        dir_count = len(output.splitlines())
        self.assertGreater(dir_count, 0, "We expect at least one directory (cloud directory) to be configured")
        self.assertEqual(cmd.returncode, 0, 'return code must be 0')


class TestDirectory(CliEAATest):

    def test_directory_health_tail(self):
        """
        Run directory command to fetch full health statuses in follow mode
        We use the RAW format for convenience (easier to read in the output)
        """
        cmd = self.cli_run('-d', '-v', 'dir', 'list', '--json', '--tail')
        time.sleep(20)  # Long enough to collect some data
        cmd.send_signal(signal.SIGINT)
        stdout, stderr = cmd.communicate(timeout=50.0)
        CliEAATest.cli_print("rc: ", cmd.returncode)
        for line in stdout.splitlines():
            CliEAATest.cli_print("stdout>", line)
        for line in stderr.splitlines():
            CliEAATest.cli_print("stderr>", line)
        self.assertGreater(len(stdout), 0, "No directory health output")


class TestCliEAA(CliEAATest):
    """
    General commands of the CLI like version or help
    """

    def test_no_edgerc(self):
        """
        Call CLI with a bogus edgerc file, help should be displayed.
        """
        cmd = self.cli_run('-e', 'file_not_exist', 'info')
        stdout, stderr = cmd.communicate()
        output = stdout.decode(encoding)
        self.assertEqual(cmd.returncode, rc_error.EDGERC_MISSING.value, f'return code must be {rc_error.EDGERC_MISSING.value}')

    def test_missing_section(self):
        """
        Call CLI with a bogus edgerc file, help should be displayed.
        """
        cmd = self.cli_run('--section', 'section_does_not_exist', 'info')
        stdout, stderr = cmd.communicate()
        output = stdout.decode(encoding)
        self.assertEqual(cmd.returncode, rc_error.EDGERC_SECTION_NOT_FOUND.value, f'return code must be {rc_error.EDGERC_MISSING.value}')


    def test_cli_version(self):
        """
        Ensure version of the CLI is displayed
        """
        cmd = self.cli_run('version')
        stdout, stderr = cmd.communicate()
        self.assertRegex(stdout.decode(encoding), r'[0-9]+\.[0-9]+\.[0-9]+\n', 'Version should be x.y.z')
        self.assertEqual(cmd.returncode, 0, 'return code must be 0')

    def test_cli_info(self):
        """
        Display tenant info
        """
        cmd = self.cli_run('info')
        stdout, stderr = cmd.communicate()
        self.assertEqual(cmd.returncode, 0, 'return code must be 0')

    def test_cli_info_usage(self):
        """
        Display tenant info with usage details
        """
        cmd = self.cli_run('info', '--show-usage')
        stdout, stderr = cmd.communicate(timeout=120)
        self.assertEqual(cmd.returncode, 0, 'return code must be 0')


if __name__ == '__main__':
    unittest.main()
