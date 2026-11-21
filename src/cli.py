#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Moon Launcher CLI entry point."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from paths import ensure_user_workspace  # noqa: E402
import launcher  # noqa: E402


def main():
    ensure_user_workspace()
    launcher.main()


if __name__ == "__main__":
    main()

