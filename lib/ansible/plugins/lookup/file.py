# (c) 2012, Daniel Hokka Zakrisson <daniel@hozac.com>
# (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = """
    name: file
    author: Daniel Hokka Zakrisson (!UNKNOWN) <daniel@hozac.com>
    version_added: "0.9"
    short_description: read file contents
    description:
        - This lookup returns the contents from a file on the Ansible controller's file system.
    options:
      _terms:
        description: path(s) of files to read
        required: True
      rstrip:
        description: whether or not to remove whitespace from the ending of the looked-up file
        type: bool
        required: False
        default: True
      lstrip:
        description: whether or not to remove whitespace from the beginning of the looked-up file
        type: bool
        required: False
        default: False
    notes:
      - if read in variable context, the file can be interpreted as YAML if the content is valid to the parser.
      - this lookup does not understand 'globbing', use the fileglob lookup instead.
    seealso:
      - ref: playbook_task_paths
        description: Search paths used for relative files.
"""

EXAMPLES = """
- ansible.builtin.debug:
    msg: "the value of foo.txt is {{ lookup('ansible.builtin.file', '/etc/foo.txt') }}"

- name: display multiple file contents
  ansible.builtin.debug: var=item
  with_file:
    - "/path/to/foo.txt"
    - "bar.txt"  # will be looked in files/ dir relative to play or in role
    - "/path/to/biz.txt"
"""

RETURN = """
  _raw:
    description:
      - content of file(s)
    type: list
    elements: str
"""

from ansible.errors import AnsibleError, AnsibleOptionsError, AnsibleLookupError
from ansible.plugins.lookup import LookupBase
from ansible.module_utils.common.text.converters import to_text
from ansible.utils.display import Display

display = Display()


class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):

        ret = []
        self.set_options(var_options=variables, direct=kwargs)

        for term in terms:
            display.debug("File lookup term: %s" % term)
            # Find the file in the expected search path
            try:
                lookupfile = self.find_file_in_search_path(
                    variables, "files", term, ignore_missing=True
                )
                display.vvvv("File lookup using %s as file" % lookupfile)
                if lookupfile:
                    b_contents, show_data = self._loader._get_file_contents(lookupfile)
                    contents = to_text(b_contents, errors="surrogate_or_strict")
                    if self.get_option("lstrip"):
                        contents = contents.lstrip()
                    if self.get_option("rstrip"):
                        contents = contents.rstrip()
                    ret.append(contents)
                else:
                    # TODO: only add search info if abs path?
                    raise AnsibleOptionsError(
                        "file not found, use -vvvvv to see paths searched"
                    )
            except AnsibleError as e:
                raise AnsibleLookupError(
                    "The 'file' lookup had an issue accessing the file '%s'" % term,
                    orig_exc=e,
                )

        return ret
