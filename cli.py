"""Entrypoint da CLI: `python cli.py <comando> [args]`.

Comandos são autodescobertos em src/app/console/commands/ (subclasses de Command).
"""

import sys

from src.support.core.console.kernel import main

if __name__ == "__main__":
    sys.exit(main())
