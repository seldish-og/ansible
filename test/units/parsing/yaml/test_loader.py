# coding: utf-8
# (c) 2015, Toshio Kuratomi <tkuratomi@ansible.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations

from collections.abc import Sequence, Set, Mapping
from io import StringIO

import unittest

from ansible import errors
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.parsing import vault
from ansible.parsing.yaml.objects import AnsibleVaultEncryptedUnicode
from ansible.parsing.yaml.dumper import AnsibleDumper

from units.mock.yaml_helper import YamlTestUtils
from units.mock.vault_helper import TextVaultSecret

from yaml.parser import ParserError
from yaml.scanner import ScannerError


class NameStringIO(StringIO):
    """In py2.6, StringIO doesn't let you set name because a baseclass has it
    as readonly property"""

    name = None

    def __init__(self, *args, **kwargs):
        super(NameStringIO, self).__init__(*args, **kwargs)


class TestAnsibleLoaderBasic(unittest.TestCase):

    def test_parse_number(self):
        stream = StringIO(
            """
                1
                """
        )
        loader = AnsibleLoader(stream, "myfile.yml")
        data = loader.get_single_data()
        self.assertEqual(data, 1)
        # No line/column info saved yet

    def test_parse_string(self):
        stream = StringIO(
            """
                Ansible
                """
        )
        loader = AnsibleLoader(stream, "myfile.yml")
        data = loader.get_single_data()
        self.assertEqual(data, "Ansible")
        self.assertIsInstance(data, str)

        self.assertEqual(data.ansible_pos, ("myfile.yml", 2, 17))

    def test_parse_utf8_string(self):
        stream = StringIO(
            """
                Cafè Eñyei
                """
        )
        loader = AnsibleLoader(stream, "myfile.yml")
        data = loader.get_single_data()
        self.assertEqual(data, "Cafè Eñyei")
        self.assertIsInstance(data, str)

        self.assertEqual(data.ansible_pos, ("myfile.yml", 2, 17))

    def test_parse_dict(self):
        stream = StringIO(
            """
                webster: daniel
                oed: oxford
                """
        )
        loader = AnsibleLoader(stream, "myfile.yml")
        data = loader.get_single_data()
        self.assertEqual(data, {"webster": "daniel", "oed": "oxford"})
        self.assertEqual(len(data), 2)
        self.assertIsInstance(list(data.keys())[0], str)
        self.assertIsInstance(list(data.values())[0], str)

        # Beginning of the first key
        self.assertEqual(data.ansible_pos, ("myfile.yml", 2, 17))

        self.assertEqual(data["webster"].ansible_pos, ("myfile.yml", 2, 26))
        self.assertEqual(data["oed"].ansible_pos, ("myfile.yml", 3, 22))

    def test_parse_list(self):
        stream = StringIO(
            """
                - a
                - b
                """
        )
        loader = AnsibleLoader(stream, "myfile.yml")
        data = loader.get_single_data()
        self.assertEqual(data, ["a", "b"])
        self.assertEqual(len(data), 2)
        self.assertIsInstance(data[0], str)

        self.assertEqual(data.ansible_pos, ("myfile.yml", 2, 17))

        self.assertEqual(data[0].ansible_pos, ("myfile.yml", 2, 19))
        self.assertEqual(data[1].ansible_pos, ("myfile.yml", 3, 19))

    def test_parse_short_dict(self):
        stream = StringIO("""{"foo": "bar"}""")
        loader = AnsibleLoader(stream, "myfile.yml")
        data = loader.get_single_data()
        self.assertEqual(data, dict(foo="bar"))

        self.assertEqual(data.ansible_pos, ("myfile.yml", 1, 1))
        self.assertEqual(data["foo"].ansible_pos, ("myfile.yml", 1, 9))

        stream = StringIO("""foo: bar""")
        loader = AnsibleLoader(stream, "myfile.yml")
        data = loader.get_single_data()
        self.assertEqual(data, dict(foo="bar"))

        self.assertEqual(data.ansible_pos, ("myfile.yml", 1, 1))
        self.assertEqual(data["foo"].ansible_pos, ("myfile.yml", 1, 6))

    def test_error_conditions(self):
        stream = StringIO("""{""")
        loader = AnsibleLoader(stream, "myfile.yml")
        self.assertRaises(ParserError, loader.get_single_data)

    def test_tab_error(self):
        stream = StringIO("""---\nhosts: localhost\nvars:\n  foo: bar\n\tblip: baz""")
        loader = AnsibleLoader(stream, "myfile.yml")
        self.assertRaises(ScannerError, loader.get_single_data)

    def test_front_matter(self):
        stream = StringIO("""---\nfoo: bar""")
        loader = AnsibleLoader(stream, "myfile.yml")
        data = loader.get_single_data()
        self.assertEqual(data, dict(foo="bar"))

        self.assertEqual(data.ansible_pos, ("myfile.yml", 2, 1))
        self.assertEqual(data["foo"].ansible_pos, ("myfile.yml", 2, 6))

        # Initial indent (See: #6348)
        stream = StringIO(""" - foo: bar\n   baz: qux""")
        loader = AnsibleLoader(stream, "myfile.yml")
        data = loader.get_single_data()
        self.assertEqual(data, [{"foo": "bar", "baz": "qux"}])

        self.assertEqual(data.ansible_pos, ("myfile.yml", 1, 2))
        self.assertEqual(data[0].ansible_pos, ("myfile.yml", 1, 4))
        self.assertEqual(data[0]["foo"].ansible_pos, ("myfile.yml", 1, 9))
        self.assertEqual(data[0]["baz"].ansible_pos, ("myfile.yml", 2, 9))


class TestAnsibleLoaderVault(unittest.TestCase, YamlTestUtils):
    def setUp(self):
        self.vault_password = "hunter42"
        vault_secret = TextVaultSecret(self.vault_password)
        self.vault_secrets = [("vault_secret", vault_secret), ("default", vault_secret)]
        self.vault = vault.VaultLib(self.vault_secrets)

    @property
    def vault_secret(self):
        return vault.match_encrypt_secret(self.vault_secrets)[1]

    def test_wrong_password(self):
        plaintext = "Ansible"
        bob_password = "this is a different password"

        bobs_secret = TextVaultSecret(bob_password)
        bobs_secrets = [("default", bobs_secret)]

        bobs_vault = vault.VaultLib(bobs_secrets)

        ciphertext = bobs_vault.encrypt(
            plaintext, vault.match_encrypt_secret(bobs_secrets)[1]
        )

        try:
            self.vault.decrypt(ciphertext)
        except Exception as e:
            self.assertIsInstance(e, errors.AnsibleError)
            self.assertEqual(
                e.message,
                "Decryption failed (no vault secrets were found that could decrypt)",
            )

    def _encrypt_plaintext(self, plaintext):
        # Construct a yaml repr of a vault by hand
        vaulted_var_bytes = self.vault.encrypt(plaintext, self.vault_secret)

        # add yaml tag
        vaulted_var = vaulted_var_bytes.decode()
        lines = vaulted_var.splitlines()
        lines2 = []
        for line in lines:
            lines2.append("        %s" % line)

        vaulted_var = "\n".join(lines2)
        tagged_vaulted_var = """!vault |\n%s""" % vaulted_var
        return tagged_vaulted_var

    def _build_stream(self, yaml_text):
        stream = NameStringIO(yaml_text)
        stream.name = "my.yml"
        return stream

    def _loader(self, stream):
        return AnsibleLoader(stream, vault_secrets=self.vault.secrets)

    def _load_yaml(self, yaml_text, password):
        stream = self._build_stream(yaml_text)
        loader = self._loader(stream)

        data_from_yaml = loader.get_single_data()

        return data_from_yaml

    def test_dump_load_cycle(self):
        avu = AnsibleVaultEncryptedUnicode.from_plaintext(
            "The plaintext for test_dump_load_cycle.", self.vault, self.vault_secret
        )
        self._dump_load_cycle(avu)

    def test_embedded_vault_from_dump(self):
        avu = AnsibleVaultEncryptedUnicode.from_plaintext(
            "setec astronomy", self.vault, self.vault_secret
        )
        blip = {
            "stuff1": [
                {"a dict key": 24},
                {"shhh-ssh-secrets": avu, "nothing to see here": "move along"},
            ],
            "another key": 24.1,
        }

        blip = ["some string", "another string", avu]
        stream = NameStringIO()

        self._dump_stream(blip, stream, dumper=AnsibleDumper)

        stream.seek(0)

        stream.seek(0)

        loader = self._loader(stream)

        data_from_yaml = loader.get_data()

        stream2 = NameStringIO("")
        # verify we can dump the object again
        self._dump_stream(data_from_yaml, stream2, dumper=AnsibleDumper)

    def test_embedded_vault(self):
        plaintext_var = """This is the plaintext string."""
        tagged_vaulted_var = self._encrypt_plaintext(plaintext_var)
        another_vaulted_var = self._encrypt_plaintext(plaintext_var)

        different_var = """A different string that is not the same as the first one."""
        different_vaulted_var = self._encrypt_plaintext(different_var)

        yaml_text = (
            """---\nwebster: daniel\noed: oxford\nthe_secret: %s\nanother_secret: %s\ndifferent_secret: %s"""
            % (tagged_vaulted_var, another_vaulted_var, different_vaulted_var)
        )

        data_from_yaml = self._load_yaml(yaml_text, self.vault_password)
        vault_string = data_from_yaml["the_secret"]

        self.assertEqual(plaintext_var, data_from_yaml["the_secret"])

        test_dict = {}
        test_dict[vault_string] = "did this work?"

        self.assertEqual(vault_string.data, vault_string)

        # This looks weird and useless, but the object in question has a custom __eq__
        self.assertEqual(vault_string, vault_string)

        another_vault_string = data_from_yaml["another_secret"]
        different_vault_string = data_from_yaml["different_secret"]

        self.assertEqual(vault_string, another_vault_string)
        self.assertNotEqual(vault_string, different_vault_string)

        # More testing of __eq__/__ne__
        self.assertTrue("some string" != vault_string)
        self.assertNotEqual("some string", vault_string)

        # Note this is a compare of the str/unicode of these, they are different types
        # so we want to test self == other, and other == self etc
        self.assertEqual(plaintext_var, vault_string)
        self.assertEqual(vault_string, plaintext_var)
        self.assertFalse(plaintext_var != vault_string)
        self.assertFalse(vault_string != plaintext_var)


class TestAnsibleLoaderPlay(unittest.TestCase):

    def setUp(self):
        stream = NameStringIO(
            """
                - hosts: localhost
                  vars:
                    number: 1
                    string: Ansible
                    utf8_string: Cafè Eñyei
                    dictionary:
                      webster: daniel
                      oed: oxford
                    list:
                      - a
                      - b
                      - 1
                      - 2
                  tasks:
                    - name: Test case
                      ping:
                        data: "{{ utf8_string }}"

                    - name: Test 2
                      ping:
                        data: "Cafè Eñyei"

                    - name: Test 3
                      command: "printf 'Cafè Eñyei\\n'"
                """
        )
        self.play_filename = "/path/to/myplay.yml"
        stream.name = self.play_filename
        self.loader = AnsibleLoader(stream)
        self.data = self.loader.get_single_data()

    def tearDown(self):
        pass

    def test_data_complete(self):
        self.assertEqual(len(self.data), 1)
        self.assertIsInstance(self.data, list)
        self.assertEqual(
            frozenset(self.data[0].keys()), frozenset(("hosts", "vars", "tasks"))
        )

        self.assertEqual(self.data[0]["hosts"], "localhost")

        self.assertEqual(self.data[0]["vars"]["number"], 1)
        self.assertEqual(self.data[0]["vars"]["string"], "Ansible")
        self.assertEqual(self.data[0]["vars"]["utf8_string"], "Cafè Eñyei")
        self.assertEqual(
            self.data[0]["vars"]["dictionary"], {"webster": "daniel", "oed": "oxford"}
        )
        self.assertEqual(self.data[0]["vars"]["list"], ["a", "b", 1, 2])

        self.assertEqual(
            self.data[0]["tasks"],
            [
                {"name": "Test case", "ping": {"data": "{{ utf8_string }}"}},
                {"name": "Test 2", "ping": {"data": "Cafè Eñyei"}},
                {"name": "Test 3", "command": "printf 'Cafè Eñyei\n'"},
            ],
        )

    def walk(self, data):
        # Make sure there's no str in the data
        self.assertNotIsInstance(data, bytes)

        # Descend into various container types
        if isinstance(data, str):
            # strings are a sequence so we have to be explicit here
            return
        elif isinstance(data, (Sequence, Set)):
            for element in data:
                self.walk(element)
        elif isinstance(data, Mapping):
            for k, v in data.items():
                self.walk(k)
                self.walk(v)

        # Scalars were all checked so we're good to go
        return

    def test_no_str_in_data(self):
        # Checks that no strings are str type
        self.walk(self.data)

    def check_vars(self):
        # Numbers don't have line/col information yet
        # self.assertEqual(self.data[0][u'vars'][u'number'].ansible_pos, (self.play_filename, 4, 21))

        self.assertEqual(
            self.data[0]["vars"]["string"].ansible_pos, (self.play_filename, 5, 29)
        )
        self.assertEqual(
            self.data[0]["vars"]["utf8_string"].ansible_pos, (self.play_filename, 6, 34)
        )

        self.assertEqual(
            self.data[0]["vars"]["dictionary"].ansible_pos, (self.play_filename, 8, 23)
        )
        self.assertEqual(
            self.data[0]["vars"]["dictionary"]["webster"].ansible_pos,
            (self.play_filename, 8, 32),
        )
        self.assertEqual(
            self.data[0]["vars"]["dictionary"]["oed"].ansible_pos,
            (self.play_filename, 9, 28),
        )

        self.assertEqual(
            self.data[0]["vars"]["list"].ansible_pos, (self.play_filename, 11, 23)
        )
        self.assertEqual(
            self.data[0]["vars"]["list"][0].ansible_pos, (self.play_filename, 11, 25)
        )
        self.assertEqual(
            self.data[0]["vars"]["list"][1].ansible_pos, (self.play_filename, 12, 25)
        )
        # Numbers don't have line/col info yet
        # self.assertEqual(self.data[0][u'vars'][u'list'][2].ansible_pos, (self.play_filename, 13, 25))
        # self.assertEqual(self.data[0][u'vars'][u'list'][3].ansible_pos, (self.play_filename, 14, 25))

    def check_tasks(self):
        #
        # First Task
        #
        self.assertEqual(
            self.data[0]["tasks"][0].ansible_pos, (self.play_filename, 16, 23)
        )
        self.assertEqual(
            self.data[0]["tasks"][0]["name"].ansible_pos, (self.play_filename, 16, 29)
        )
        self.assertEqual(
            self.data[0]["tasks"][0]["ping"].ansible_pos, (self.play_filename, 18, 25)
        )
        self.assertEqual(
            self.data[0]["tasks"][0]["ping"]["data"].ansible_pos,
            (self.play_filename, 18, 31),
        )

        #
        # Second Task
        #
        self.assertEqual(
            self.data[0]["tasks"][1].ansible_pos, (self.play_filename, 20, 23)
        )
        self.assertEqual(
            self.data[0]["tasks"][1]["name"].ansible_pos, (self.play_filename, 20, 29)
        )
        self.assertEqual(
            self.data[0]["tasks"][1]["ping"].ansible_pos, (self.play_filename, 22, 25)
        )
        self.assertEqual(
            self.data[0]["tasks"][1]["ping"]["data"].ansible_pos,
            (self.play_filename, 22, 31),
        )

        #
        # Third Task
        #
        self.assertEqual(
            self.data[0]["tasks"][2].ansible_pos, (self.play_filename, 24, 23)
        )
        self.assertEqual(
            self.data[0]["tasks"][2]["name"].ansible_pos, (self.play_filename, 24, 29)
        )
        self.assertEqual(
            self.data[0]["tasks"][2]["command"].ansible_pos,
            (self.play_filename, 25, 32),
        )

    def test_line_numbers(self):
        # Check the line/column numbers are correct
        # Note: Remember, currently dicts begin at the start of their first entry
        self.assertEqual(self.data[0].ansible_pos, (self.play_filename, 2, 19))
        self.assertEqual(self.data[0]["hosts"].ansible_pos, (self.play_filename, 2, 26))
        self.assertEqual(self.data[0]["vars"].ansible_pos, (self.play_filename, 4, 21))

        self.check_vars()

        self.assertEqual(
            self.data[0]["tasks"].ansible_pos, (self.play_filename, 16, 21)
        )

        self.check_tasks()
