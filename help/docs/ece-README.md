# ECE 提取 · 归档索引

> ECE（等效电路提取）相关的全部资产集中在此登记
> 更新日期：2026-10-21

## 入口

| 要做的事 | 看这里 |
|---|---|
| **怎么用**（完整步骤、配置、故障处置） | `help/docs/ece-export-manual.md` |
| **跑一次导出** | `scripts/run_ece_export.py --config <配置>` |

## 代码

| 文件 | 行数 | 职责 |
|---|---|---|
| `scripts/run_ece_export.py` | 约 200 | 命令行入口：读配置 → 连 Motor-CAD → 调导出 → 报告 |
| `src/motorcad_controller/ece_exporter.py` | 约 650 | 核心：网格推导、反电势、饱和图、查表构建、TXT/SML 写出 |
| `tests/test_ece_exporter.py` | 约 250 | 32 项单测（纯计算部分，不需 Motor-CAD） |

## 配置（每套网格一份）

| 配置 | 段数 | 点数/轴 | 步长 (A) | 负载点 | 耗时 | 产物目录 |
|---|---|---|---|---|---|---|
| `e11_ece_config.json` | 8 | 9 | 108.25 | 81 | 5.2 min | `results/e11-ece/` |
| `e11_ece_config_20x20.json` | 20 | 21 | 43.30 | 441 | 29.5 min | `results/e11-ece-20x20/` |
| `e11_ece_config_41x41.json` | 40 | 41 | 21.65 | 1,681 | 约 112 min | `results/e11-ece-41x41/` |
| `e11_ece_config_61x61.json` | 60 | 61 | 14.43 | 3,721 | 243.5 min | `results/e11-ece-61x61/` |
| `e11_ece_config_81x81.json` | 80 | 81 | 10.83 | 6,561 | 约 7.2 h | （未跑） |
| `e11_ece_config_91x91.json` | 90 | 91 | 9.62 | 8,281 | 约 9 h | `results/e11-ece-91x91/` |

> 网格点数必须为奇数（Motor-CAD 要求含 Id=0），所以「20×20」实为 21 点/轴。

## 产物

| 目录 | 状态 | 说明 |
|---|---|---|
| `results/e11-ece/` | ✅ 完成 | 8×8，跑通链路用 |
| `results/e11-ece-20x20/` | ✅ 完成 | MTPA 主表 |
| `results/e11-ece-61x61/` | ✅ 完成 | 高精度，弱磁表用 |
| `results/e11-ece-91x91/` | 🔄 运行中 | 最高精度 |

## 官方原件（对照用）

| 文件 | 用途 |
|---|---|
| `models/motorcad/ece/MotorCAD_ECE_Export.py` | 随 Motor-CAD 安装的官方教程脚本 —— **格式标准答案** |
| `models/motorcad/ece/ece_config.json` | 官方配置样例 |
| `help/repos/pymotorcad/examples/links/ece_export_for_twinbuilder.py` | PyMotorCAD 官方示例（779 行） |

> 改过 SML/TXT 生成逻辑后，务必与官方原件产物做一次逐字符比对（方法见手册第八节）。

## 相关设计文档

| 文档 | 内容 |
|---|---|
| `docs/design/e11-control-model.md` §4 | ECE 提取流程设计、风险表 |
| `docs/requirements/e11-control-model.md` F2 | ECE 提取的验收标准 |
| `docs/batches/2026-10-21-ece-pwl-fix.md` | pwl 缺陷的定位与修复记录 |
