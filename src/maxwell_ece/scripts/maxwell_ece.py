"""Windows-friendly script wrapper; use the pmsm Python environment."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from maxwell_ece_pkg.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
