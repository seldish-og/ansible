#!/usr/bin/python
from __future__ import annotations

import json


def main():
    print(json.dumps(dict(changed=False, source="user_ansible_bullcoll")))


if __name__ == "__main__":
    main()
