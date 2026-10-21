# 本次 ECE 项目参考文档与代码

环境：AEDT 2026 R1、PyAEDT 1.4.0、`pmsm` Python。以下链接指向本次实际查阅的本机文件；官方 PDF 页码指页脚的章节页码，不是查看器中的总页序号。

建议先看厂家 `MaxwlECE.vbs` 和 `Dedicated Elements.aclb`，再对照本项目的 `write_ece_netlist`、`_run_live`。

## 1. 官方手册

| 文档 | 阅读位置 | 本次用途 |
| --- | --- | --- |
| [Maxwell Scripting Guide](<E:/ANSYS Inc/v261/AnsysEM/Help/Maxwell/MaxwellScriptingGuide.pdf>) | `ExportECEData`，15-14，示例延续至下一页 | 核对 `AnalysisSetup.ExportECEData` 参数名称、variation、setup 和输出目录；官方返回值为 None。 |
| [Maxwell Help](<E:/ANSYS Inc/v261/AnsysEM/Help/Maxwell/Maxwell.pdf>) | `ECE3 Model`，27-21、27-22 及后续说明 | 电流扫描列表、`PhAngIntervals` 的 DQ/αβ/幅相扫描含义，以及 ECE3 与 ECER 的组合。 |
| 同上 | `ECER Model`，27-47、27-48 及后续说明 | 电角度/机械角度、转角区间、极数、槽数、斜槽和 ABC/DQ0/LdLqFm 输出；槽数会影响零电流齿槽采样。 |

PDF 的全文检索文本保存在 `research/MaxwellScriptingGuide.txt` 和 `research/Maxwell.txt`，可用关键词搜索。

## 2. 厂家库定义与示例代码

| 文件 | 重点位置 | 本次用途 |
| --- | --- | --- |
| [Dedicated Elements.aclb：ECE3](<E:/ANSYS Inc/v261/AnsysEM/syslib/Maxwell Circuit Elements/Dedicated Elements.aclb:73>) | 第 87 行 `MaxCirNetList` | 原生 `.MODEL ... ECE3` 模型卡模板，包含 Windings、Sweeps、PAngN、Res、Ind。 |
| [Dedicated Elements.aclb：ECER](<E:/ANSYS Inc/v261/AnsysEM/syslib/Maxwell Circuit Elements/Dedicated Elements.aclb:106>) | 第 122 行 `MaxCirNetList` | 原生 `.MODEL ... ECER` 模板，包含 RAngM、EDeg、RAngN、Skew、Poles、Slots、DQOutput。 |
| [MaxwlECE.vbs](<E:/ANSYS Inc/v261/AnsysEM/Examples/Twin Builder/Components/Interfaces/RMxprt/RMxprt PMSM.aedtresults/FourPole_PMSM.results/DV14_SOL1_V0.MExportData/MaxwlECE.vbs:29>) | 第 29 行 ECE3、第 48 行 ECER、第 75 行 CreateGround、第 83 行 ExportNetList | 厂家随安装包附带的 ECE 电路生成示例；明确创建两个模型和 Ground 后导出网表。文件头注明由 RMxprt 2016.0 生成，因此本项目另外使用当前版本库定义和实际导出来核对。 |
| [厂家旧版 ECE SML 样例](<E:/ANSYS Inc/v261/AnsysEM/Examples/Twin Builder/Applications/Motor Equivalent Circuit Toolkit/ECER_Model1.sml>) | 文件头、PORT 与内部元件 | 参考 ECE 的电气/机械端口和模型结构。该旧样例是 SMLDEF；本机真实新导出是 MODELDEF，两者现在都支持。 |

## 3. 实际调用的 PyAEDT 源码

以下均为 `pmsm` 环境安装的 PyAEDT 1.4.0 源码。

| 调用 | 源码 | 用途 |
| --- | --- | --- |
| `Maxwell.edit_external_circuit` | [maxwell.py:2482](C:/Env/miniconda3/envs/pmsm/Lib/site-packages/ansys/aedt/core/maxwell.py:2482) | 将生成的 `.sph` 接入 Maxwell；最终调用原生 `EditExternalCircuit`。 |
| `change_design_settings` | [design.py:3630](C:/Env/miniconda3/envs/pmsm/Lib/site-packages/ansys/aedt/core/application/design.py:3630) | 在 ECE 工作设计中关闭 `EnableTranTranLinkWithSimplorer`，解决实际导入报错。 |
| `save_project` | [design.py:4491](C:/Env/miniconda3/envs/pmsm/Lib/site-packages/ansys/aedt/core/application/design.py:4491) | 求解前后保存工作工程。 |
| `analyze_setup` | [analysis.py:1984](C:/Env/miniconda3/envs/pmsm/Lib/site-packages/ansys/aedt/core/application/analysis.py:1984) | 对指定 setup 求解，并设置每任务核心数。 |
| `MaxwellCircuit.export_netlist_from_schematic` | [maxwellcircuit.py:222](C:/Env/miniconda3/envs/pmsm/Lib/site-packages/ansys/aedt/core/maxwellcircuit.py:222) | 本次 Ground 对照实验使用的原生原理图网表导出。 |
| `create_component_from_sml` | [primitives_twin_builder.py:600](C:/Env/miniconda3/envs/pmsm/Lib/site-packages/ansys/aedt/core/modeler/circuits/primitives_twin_builder.py:600) | 本次 Twin Builder 导入与放置测试；内部使用 `ImportModelsFromFile`。 |

`ExportECEData` 在本机 PyAEDT 的 Maxwell 高层类中没有专用封装；本项目按官方脚本手册调用 `m2d.oanalysis.ExportECEData(...)`。

## 4. 本项目实现代码

| 入口 | 位置 |
| --- | --- |
| AEDT 文本读取、设计枚举 | [core.py:166](src/maxwell_ece/ece/core.py:166) |
| 根据模型变量生成配置草案 | [core.py:203](src/maxwell_ece/ece/core.py:203) |
| 配置及扫描参数校验 | [core.py:302](src/maxwell_ece/ece/core.py:302) |
| 创建工程工作副本 | [core.py:443](src/maxwell_ece/ece/core.py:443) |
| 生成 ECE3 / ECER 网表 | [core.py:485](src/maxwell_ece/ece/core.py:485) |
| 实际 AEDT 运行、保存、名义 variation、导出及异常信息 | [core.py:529](src/maxwell_ece/ece/core.py:529) |
| 多进程并行调度 | [core.py:736](src/maxwell_ece/ece/core.py:736) |
| 命令行入口 | [cli.py:67](src/maxwell_ece/ece/cli.py:67) |
| 六个 MCP 工具 | [mcp_server.py:15](src/maxwell_ece/ece/mcp_server.py:15) |
| 测试代码 | [test_core.py](src/maxwell_ece/tests/test_core.py) |

## 5. 本次实际生成的对照文件和结果

- [带 Ground 的原生 Maxwell Circuit 工程](src/maxwell_ece/research/native-ground-reference.aedt)
- [带 Ground 的原生网表](src/maxwell_ece/research/native-ground-reference.sph) / [添加 Ground 之前的网表](src/maxwell_ece/research/native-without-ground.sph)
- [Ground 对照记录](src/maxwell_ece/research/native-ground-comparison.json)：两模型均为零引脚，加 Ground 前后网表相同。
- [Healthy 实际 ECE](src/maxwell_ece/outputs/PMSM_Healthy/ece_model.sml) / [实际扫描表](src/maxwell_ece/outputs/PMSM_Healthy/ece_table.txt) / [实际使用配置](src/maxwell_ece/outputs/PMSM_Healthy/config-used.json)
- [UD 实际 ECE](src/maxwell_ece/outputs/PMSM_UD/ece_model.sml) / [实际使用配置](src/maxwell_ece/outputs/PMSM_UD/config-used.json)
- [Twin Builder 导入测试工程](src/maxwell_ece/work/twinbuilder-import-check/ece_import_check.aedt) / [导入记录](src/maxwell_ece/research/root-twinbuilder-import.json)
- [运行结果汇总](src/maxwell_ece/outputs/run-summary.json)

这些实测结果使用 0/1 A、三个转角区间及 Slots=0，只用于确认提取和导入链路；正式精度扫描参数仍需另行确定。
