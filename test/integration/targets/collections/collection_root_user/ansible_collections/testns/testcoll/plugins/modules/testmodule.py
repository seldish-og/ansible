#!/usr/bin/python
from __future__ import annotations

import json

DOCUMENTATION = r"""
module: testmodule
description: for testing
extends_documentation_fragment:
  - testns.testcoll.frag
  - testns.testcoll.frag.other_documentation
"""


def main():
    print(json.dumps(dict(changed=False, source="user")))


if __name__ == "__main__":
    main()
