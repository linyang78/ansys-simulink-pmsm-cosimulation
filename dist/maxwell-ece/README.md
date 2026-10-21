# maxwell-ece — Maxwell 原生 ECE 提取

自包含工具包。从 Maxwell 2D 的 Transient 解提取 ECE3 + ECER 模型，产出 Twin Builder 可直接导入的
`.sph` 网表、`.sml` 模型和 `.txt` 查表。

**与 Motor-CAD ECE 的区别**：Motor-CAD 走解析模型（快，5–250 min）；这里走 Maxwell 有限元解（准，但慢）。
故障样机、几何改型后的模型只能用这条路径。

## 五步流程

```
inspect → draft → validate → prepare → run
```

前两步离线，不启动 AEDT。`run` 才真正求解。

| 步 | 做什么 | 要 AEDT 吗 |
|---|---|---|
| `inspect` | 读 `.aedt` 文本，列出 design / setup / 绕组组 / 运动 | 否 |
| `draft` | 从 inspection 生成配置草案 | 否 |
| `validate` | 校验配置完整性 | 否 |
| `prepare` | 复制到隔离工作目录 | 否 |
| `run` | 挂外电路、求解、导出 ECE | **是** |

## 调用契约

包根目录下执行：

```powershell
$py  = 'python'
$cli = 'scripts/maxwell_ece.py'
$mot = 'models/e11_PMSM_IPM.aedt'

# 1. 读工程结构
& $py $cli inspect $mot --write config/inspection.json

# 2. 生成配置草案（多 design 必须显式指定）
& $py $cli draft $mot --design PMSM_Healthy --setup Setup1 --write config/draft.json

# 3. 校验
& $py $cli validate config/draft.json --inspection config/inspection.json

# 4. 复制到隔离目录
& $py $cli prepare config/draft.json

# 5. 求解并导出
& $py $cli run config/draft.json
```

### ⚠️ `draft` 不会替你挑 design

多个 design 或 setup 时，**必须**显式给 `--design` 和 `--setup`。
省略会报错停下，不会默认选第一个——选错一次要白跑几小时。

### 参数

| 参数 | 适用 | 说明 |
|---|---|---|
| `--write <path>` | inspect / draft | 输出文件路径 |
| `--design <名>` | draft | 必填（多 design 时） |
| `--setup <名>` | draft | 必填（多 setup 时） |
| `--inspection <path>` | validate | 校验时对照的 inspection |
| `--allow-unreviewed` | run | 跳过 `reviewed` 标志检查 |

## 配置说明

配置由 `draft` 生成，关键字段：

| 字段 | e11 取值 | 说明 |
|---|---|---|
| `design` / `setup` | `PMSM_Healthy` / `Setup1` | 目标 |
| `winding_groups` | `WG_Ph1_P1` 等三个 | 三相绕组组名 |
| `ece.current_sweeps` | `0A, 1A, 2A`（smoke） | 电流扫描点 |
| `ece.ph_ang_intervals` | **2** | Id/Iq 双向扫描（IPM 弱磁需负 Id） |
| `ece.rot_ang_max` | `360deg` | 转子角范围 |
| `ece.rot_ang_intervals` | 360 | 转角区间数 |
| `ece.poles` / `slots` | 8 / 48 | e11 极数与槽数 |
| `ece.resistance` | 0.013377 Ω | 相电阻 |
| `ece.inductance` | 6.027e-6 H | 端部漏感 |
| `reviewed` | `false` | **人工复核后改 true** |

### 扫描规模

`current_sweeps` 点数 × `rot_ang_intervals` = FEA 工况数。

| 电流点 | 转角区间 | 工况数 | 估时 |
|---|---|---|---|
| 2（smoke） | 3 | 6 | 约 55 秒 |
| 7 | 120 | 840 | 约 1 小时 |
| 11 | 361 | 3971 | 约 4.5 小时 |

## 产物

```
<output_dir>/<run-id>/
├── ece_model.sml              导入 Twin Builder 用这个
├── ece_table.txt              可读查表
├── <design>.sph               外电路网表（Maxwell Circuit 语法）
└── logfile                    原生求解日志
```

`.sph` 由厂家模板 `Dedicated Elements.aclb` 的语法生成：

```
.MODEL ECE_Model1_ECE3 ECE3 (Windings=WG_Ph1_P1,WG_Ph2_P1,WG_Ph3_P1 Sweeps=... PAngN=2 Res=... Ind=...)
.MODEL ECE_Model1_ECER ECER (RAngM=360deg EDeg=0 RAngN=360 Skew=0deg Poles=8 Slots=48 DQOutput=0)
.end
```

**ECE3** 扫三相电流，**ECER** 扫转子位置。两者组合成旋转电机的完整模型。

## 核心 API 链路

pyaedt 1.4.0 没有直接暴露 ECE 导出，走原生接口：

```python
write_ece_netlist(...)                              # 按厂家模板生成 .sph
m2d.edit_external_circuit(netlist_file_path=sph)    # 挂载到 Maxwell
m2d.oanalysis.ExportECEData(export_args)            # 原生 ECE 导出
```

`ExportECEData` 成功时返回 `None`——**不能用返回值判断成败**，要看文件是否真的落盘。

## 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 求解或导出失败 |
| 2 | 输入问题（配置非法 / 工程不存在 / design 找不到） |
| 3 | 环境问题（AEDT 起不来 / pyaedt 版本不符） |

## 环境要求

| 依赖 | 版本 |
|---|---|
| Python | 3.10+ |
| pyaedt | 1.4.0（`import ansys.aedt.core`） |
| AEDT | 2026 R1 |
| psutil | 任意（进程监控） |
| mcp | 可选（只做 MCP 服务时需要） |

## 目录结构

```
maxwell-ece/
├── README.md                        ← 本文件
├── scripts/
│   └── maxwell_ece.py               ← 命令行入口
├── src/maxwell_ece_pkg/
│   ├── __init__.py
│   ├── cli.py                       ← 参数解析、子命令
│   ├── core.py                      ← 解析、网表生成、运行
│   └── mcp_server.py                ← MCP 服务（可选）
├── config/
│   └── ece_config.example.json      ← 配置结构示例
├── models/
│   └── e11_PMSM_IPM.aedt            ← 样例工程（双 design）
└── tests/
    ├── test_core.py
    ├── test_cli.py
    └── fixtures/logfile             ← 真实求解日志样本
```

## 自检

```powershell
# 单测（不需要 AEDT，约 8 秒）
python -m unittest discover -s tests

# 离线读工程（不需要 AEDT）
python scripts/maxwell_ece.py inspect models/e11_PMSM_IPM.aedt
```

## 不做什么

- **不改源工程**：`prepare` 复制到隔离目录，原文件只读
- **不做 Motor-CAD 路径**：那是另一个包（`ece-export`）
- **不做故障建模**：只提取给定几何的 ECE，故障几何要先在 Maxwell 里建好
