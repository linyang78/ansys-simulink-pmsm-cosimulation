"""Maxwell2D → Twin Builder 原生 ECE 提取 — 命令行入口。

自包含包：包代码在 `src/maxwell_ece_pkg/`，本脚本把 `src/` 加入模块搜索路径。

用法：
    python scripts/maxwell_ece.py inspect  models/e11_PMSM_IPM.aedt
    python scripts/maxwell_ece.py draft    models/e11_PMSM_IPM.aedt \\
        --design PMSM_Healthy --setup Setup1 --write config/draft.json
    python scripts/maxwell_ece.py validate config/draft.json --inspection config/inspection.json
    python scripts/maxwell_ece.py prepare  config/draft.json
    python scripts/maxwell_ece.py run      config/draft.json
"""

import sys
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[1]
SRC = PKG_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from maxwell_ece_pkg.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
