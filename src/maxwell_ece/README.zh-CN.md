# Maxwell2D 到 Twin Builder 原生 ECE

参考来源、官方手册章节、厂家示例和源码定位见 [参考文档与代码索引](docs/REFERENCES.md)。

这个子项目提供一条可审查的 Maxwell2D → Twin Builder ECE 流程。它把 AEDT 工程选择、参数草案、结构校验、隔离副本和真实运行分成五步：

`inspect → draft → validate → prepare → run`

离线步骤不启动 AEDT。`inspect` 直接读取 `.aedt` 文本，用平衡 `$begin/$end` 扫描保留 `VariableProp` 原始表达式；它会列出所有 Maxwell2DModel、Transient setup、Winding Group 和旋转运动。不会猜测绕组极性、机械轴方向、对称周期或额定点安全上限。

实际 `models/aedt/E11_FULL/e11_PMSM_IPM.aedt` 含 `PMSM_Healthy` 与 `PMSM_UD` 两个设计，且每个设计有 `Setup1`、`Setup2`；因此多设计或多 setup 时必须显式传入 `--design` 和 `--setup`，draft 不会替用户选择。

## 快速开始

以下命令在 `src/maxwell_ece/` 目录下执行，模型路径相对仓库根。

```powershell
$py  = 'C:\Env\miniconda3\envs\pmsm\python.exe'
$cli = 'scripts\maxwell_ece.py'
$mot = '..\..\models\aedt\E11_FULL\e11_PMSM_IPM.aedt'

& $py $cli inspect  $mot --write config\inspection.json
& $py $cli draft    $mot --design PMSM_Healthy --setup Setup1 --write config\draft.json
& $py $cli validate config\draft.json --inspection config\inspection.json
& $py $cli prepare  config\draft.json
```

工程含 `PMSM_Healthy` 与 `PMSM_UD` 两个 design、每个 design 有 `Setup1` 与 `Setup2`，
所以 `--design` 和 `--setup` 必须显式给出；`draft` 不会替用户挑。

编辑 `draft.json`，确认 design/setup、三绕组顺序、扫描点、单位、极性、运动轴、机械周期和输出格式后，将 `reviewed` 改为 `true`。`run` 默认仍会检查这个人工校验标志：

```powershell
& $py $cli run config\draft.json
```

真实运行已经在隔离副本上完成 smoke 验证；正式精度生产扫描仍须由用户复核草案中的 setup、相序、极性、扫描点和角度范围后再执行。`run --offline` 仍可用于验证隔离准备路径，不会创建桌面。

## ECE 参数

`.sph` 由厂家 Dedicated Elements 语法生成，包含 ECE3 和 ECER 两个模型以及 `.end`：

```text
.MODEL ECE_Model1_ECE3 ECE3 (Windings=WG_Ph1_P1,WG_Ph2_P1,WG_Ph3_P1 Sweeps=... PAngN=2 Res=... Ind=...)
.MODEL ECE_Model1_ECER ECER (RAngM=360deg EDeg=... RAngN=360 Skew=0deg Poles=8 Slots=48 DQOutput=0)
.end
```

`ph_ang_intervals=2` 是全 dq 默认值；也支持 `0`、`1`、`3` 或 `>=12`。`output` 支持 `0=ABC`、`1=DQ0` 和 `2=LdLqFm`。`in_electrical_degrees=false` 表示 `RotAngMax` 使用机械角；它与 `PhasorAngle`、`PhaseAdvance` 和初始位置不同，后面三者只作为快照候选供人工校验。参数必须带单位，电流扫描点必须包含 `0A`、严格升序且无重复。默认草案用 `[0A, 1A, 2A]` 做小型 smoke 扫描，并单独保留模型 `IPeak` 作为建议上限来源。`rot_ang_max=360deg` 只是保守建议，故障或非对称模型必须人工确认机械周期。

## Live 运行边界

`prepare` 为每次运行建立唯一目录，只复制 `.aedt`，不混入已有 `.aedtresults`。live `run` 使用 `Maxwell2d(project=<prepared copy>, design=..., new_desktop=True, close_on_exit=True)`，读取真实 Transient design、三绕组和旋转 motion；必要时仅在副本通过 `boundary.props['Type']='External'; boundary.update()` 修改绕组，调用 `edit_external_circuit(netlist_file_path=...)`、`analyze_setup(setup, cores=...)` 和 `oanalysis.ExportECEData([...])`。

`ExportECEData` 返回 `None` 不会被当作失败；最终证据来自新生成的非空 `.sml`，且必须有行首 `MODELDEF` 或旧版 `SMLDEF` 声明以及 `PORT` 或 `INTERN`。同目录文件会写入 SHA-256 manifest。当前真实证据覆盖 AEDT 求解、ECE 导出和 Twin Builder 原生导入；物理精度仍取决于正式扫描参数和后续拟合验证。

同一个 Twin Builder 工程同时导入多个模型时，应在各份配置的 `ece.device_name` 中使用不同名称。默认名称 `ECE_Model1_ECER` 适合单模型 smoke，不适合 Healthy 与 UD 并列导入。

## 已完成的真实 smoke 验证

验证输入为 `models/aedt/E11_FULL/e11_PMSM_IPM.aedt` 的隔离副本，环境为 AEDT 2026 R1、PyAEDT 1.4.0 和 `pmsm` 环境。Healthy/Setup1 的单任务 smoke 使用 `0A, 1A`、`rot_ang_intervals=3`、`slots=0`，求解约 55 秒；求解后保存成功，原生导出生成 `ece_model.sml`（5675 bytes）和 `ece_table.txt`（3707 bytes），`.sml` 的真实头为 `MODELDEF ECE_Model1_ECER`。带 Ground 与不带 Ground 的原生导出结果一致，Ground 不产生额外 pin。

该 `.sml` 已由 Twin Builder 原生 `ImportModelsFromFile` 导入并完成 placement，组件有 8 个 pin：`A0 X0 B0 Y0 C0 Z0 ROT1 ROT2`；原生导入诊断为 0 errors。随后 Healthy 与 UD 两个独立任务以两个 Desktop 并行运行，均为 `solved` 并正常关闭，耗时约 53 秒和 55 秒，日志见 `research/live-parallel-20261015.log`，最终导出复制到 `outputs/PMSM_Healthy` 与 `outputs/PMSM_UD`。配置、文件哈希及实测结果见 `outputs/run-summary.json`。

上述 `0A, 1A`、3 个转角区间和 `slots=0` 只是连通性 smoke 参数，用于证明副本、求解、导出、保存和导入链路，不代表正式精度生产配置。正式运行前仍需按实际额定电流、机械周期、槽数和故障定义复核并更新配置。

批量运行使用 `ProcessPoolExecutor` 的 `spawn` 上下文，每个 job 使用独立副本和 AEDT Desktop；`--max-parallel` 默认 1，可用 `--total-cores` 限制 `max_parallel * 最大 job cores`。MCP 薄层位于 `ece/mcp_server.py`，通过 stdio 暴露相同的 inspect/draft/validate/prepare/run/batch 函数，不复用共享 AEDT 会话。

复跑已验证的小规模并行测试：

```powershell
& $py $cli batch config\archive\smoke-parallel-PMSM_Healthy.json config\archive\smoke-parallel-PMSM_UD.json --max-parallel 2 --total-cores 2
```

启动本地 MCP 服务使用 `& $py $cli mcp`；Codex 配置示例在 `config/mcp-config.toml`。每次运行创建新的工作目录。

## 测试

```powershell
C:\Env\miniconda3\envs\pmsm\python.exe -m unittest discover -s tests -v
```

离线测试覆盖实际解析、模板、隔离准备和 fake live 编排；真实 AEDT/Twin Builder 结果以本节的运行证据为准。离线测试本身不替代许可证、求解收敛和物理精度验证。

## Full 360 正式候选

`config/full360-PMSM_Healthy.json` 是用户复核后的正式候选：原始
`models/aedt/E11_FULL/e11_PMSM_IPM.aedt` 的 `PMSM_Healthy/Setup1`，360°机械角、
1440 个区间（0.25°）、`EDeg=false`、`PhAngIntervals=2`、`Slots=0`、ABC
输出（0），电流幅值为 `0/21.65/43.3/108.25/216.5/324.75/433A`。433A
只是源模型 `IPeak` 的候选值，不是额定电流结论；源模型实际 48 槽几何不变。
正式输出位于独立的 `work/formal-full360-PMSM_Healthy-20261017`，不会覆盖
历史 smoke 结果。`initial-full360-3mag-PMSM_Healthy.json` 是独立的
`0/216.5/433A` 初始剖面，明确标记为未进行 production validation。

每个 prepare/live 任务在隔离目录写入 `progress.json` 和
`timing-result.json`。同步 `analyze_setup` 期间后台只读 tail 原生
`logfile`/`*.aedtresults`，没有可信 native 点计数时进度显示未知百分比和
不可用 ETA；只有原生日志显式提供合法计数时才显示百分比。批量任务可用
`batch ... --progress-json <JSON>` 另写聚合进度，`--max-parallel`、
`--total-cores` 和每份配置的 `cores` 继续控制并行资源。
