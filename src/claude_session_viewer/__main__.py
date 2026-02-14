"""Entry point for `python -m claude_session_viewer`."""

import sys


def main():
    from claude_session_viewer.app import run
    sys.exit(run())


if __name__ == "__main__":
    main()
