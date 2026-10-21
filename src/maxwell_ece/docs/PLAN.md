# Maxwell 2D PMSM 原生 ECE 提取方案

## 目标与边界

本子项目从用户指定的 AEDT 工程中选择一个或多个 Maxwell 2D PMSM 设计，使用 AEDT 2026 R1 原生 ECE 能力导出供 Twin Builder 使用的 `.sml`。运行环境为 `C:\Env\miniconda3\envs\pmsm\python.exe` 和 PyAEDT 1.4.0。

新增内容只放在 `versions/v0.3/maxwell_ece`。输入 `.aedt` 只读，每项任务先复制工程，再修改副本。v0.1、v0.2、既有 v0.3 Maxwell/Twin Builder/P3 资产及 `versions/v0.3/config/workflow.json` 均不修改。

旧 P3 求解可以继续运行。新任务使用 `new_desktop=True`、独立工程副本和独立输出目录，不连接、激活、保存或关闭既有 AEDT 会话。是否同时启动真实 ECE 任务由 `max_parallel`、每任务核心数、许可证和主机可用资源共同决定；不以“存在其他 AEDT 进程”作为一刀切阻塞条件。当前 v0.3 已完成受资源预算控制的真实单任务和双任务并行 smoke；正式精度扫描仍需用户复核配置参数。

第一版范围是旋转三相 PMSM 的 `ECE3_Model + ECER_Model`。原生 ECE 并不只支持三相：`ECEW_Model` 可逐绕组组合为多相模型，另有 `ECE6_Model` 等；这些路径留作后续扩展，第一版遇到非三相设计时明确报告不支持，不猜测映射。

## 已核实的原生接口

AEDT 系统库 `E:\ANSYS Inc\v261\AnsysEM\syslib\Maxwell Circuit Elements\Dedicated Elements.aclb` 给出了模型卡的正式定义：`ECE3_Model` 在第 73–89 行，`ECER_Model` 在第 106–123 行，`ECEW_Model` 在第 140–155 行。三相旋转 PMSM 使用：

```text
.MODEL <name> ECE3 (Windings=<A,B,C> Sweeps=<list> PAngN=<n> Res=<r> Ind=<l>)
.MODEL <name> ECER (RAngM=<angle> EDeg=<bool> RAngN=<n> Skew=<angle> Poles=<p> Slots=<q> DQOutput=<0|1|2>)
```

PyAEDT 1.4.0 中：

- `Maxwell.edit_external_circuit` 位于 `C:\Env\miniconda3\envs\pmsm\Lib\site-packages\ansys\aedt\core\maxwell.py:2482`，最终调用 AEDT `EditExternalCircuit`；
- `MaxwellCircuit.export_netlist_from_schematic` 位于 `...\ansys\aedt\core\maxwellcircuit.py:222`，可作为兼容性诊断路径；
- PyAEDT `maxwell.py` 没有 ECE 导出的高层封装。

因此第一版直接按厂家系统库生成最小 `.sph`，在工程副本中用 `edit_external_circuit` 载入。导出使用已记录、参数形状固定的 AEDT 原生调用：

```python
app.oanalysis.ExportECEData([
    "NAME:Export Data",
    "Design Variation:=", variation,
    "Solve Setup Name:=", setup_name,
    "Export Directory:=", export_directory,
])
```

证据为 `E:\ANSYS Inc\v261\AnsysEM\Help\Maxwell\MaxwellScriptingGuide.pdf` 第 15-14 页；文本定位为 `research/MaxwellScriptingGuide.txt:41146-41181`。该调用返回 `None`，成功依据调用无异常及导出文件判断，不能依据返回值判断。

Maxwell 帮助中的输入语义位于 `E:\ANSYS Inc\v261\AnsysEM\Help\Maxwell\Maxwell.pdf`：

- ECE3：`research/Maxwell.txt:154718-154827`；
- ECER：`research/Maxwell.txt:155778-155885`；
- ECEW：`research/Maxwell.txt:156266-156331`。

ECE3 要求三个按相序排列的 winding；`PhAngIntervals=0/1/2` 为 DQ 扫描，`3` 为两相 αβ 扫描，`>=12` 为电流幅值/相角扫描。ECER 扫描转子位置；`Output=0/1/2` 分别输出 ABC 磁链、DQ0 磁链、Ld/Lq/Fm 基波模型。ECE 执行时普通 Transient setup 的 Stop Time 和 Timestep 被忽略，求解器按 ECE 扫描表逐点运行。

文档指出 ECE3+ECER 可以利用绕组对称性，并给出 120 电角度这一常见经验值，但不同机器可能需要更大或更小范围。工具不得无条件采用 120 电角度、360 机械角度、`PhAngIntervals=2` 或其他对称性假设；这些只能作为带说明的草案字段，由用户校验。

## 五阶段工作流

### 1. inspect

`inspect` 只读 `.aedt`，记录源文件 SHA-256，并列出 Maxwell2D 设计、solution type、setup、winding、motion 和相关变量候选。

离线结果是配置建议，不是 AEDT 运行时权威读回。PyAEDT 1.4.0 的通用 AEDT parser 会丢失部分重复或嵌套 `VariableProp`，因此离线检查采用保守文本扫描并保留原始表达式。真正运行时再由新建 AEDT 会话核对所选设计。

当前用户输入为 `models/aedt/E11_FULL/e11_PMSM_IPM.aedt`。离线检查已识别两个 Maxwell 2D Transient 设计 `PMSM_Healthy` 和 `PMSM_UD`；两者各有 `Setup1`、`Setup2`、三个相绕组和旋转 motion。设计和 setup 已在真实 smoke 中分别精确选择并验证；相序、极性、正式扫描参数和角度范围仍需用户校验。

### 2. draft

`draft` 为一个设计生成一份 JSON。工程含多个设计时必须用精确设计名选择；多设计任务通过多份配置表达，避免在一个可写工程副本中并发切换设计。

草案尽量从模型提出 design、setup、variation、三个 winding 的顺序、ECE 电流/相角/转角扫描、极数、槽数、skew、输出类型、电阻和端部漏感。不能可靠推导的值保持空值或附带警告，不补造数字。

相序/极性、setup、电流范围、对称性、角度范围/单位和输出类型必须人工查看。校验后只需把 `reviewed` 设为 `true`；不引入审批人、时间戳或签字流程。

### 3. validate

`validate` 不启动 AEDT，检查必填字段、源文件哈希、所选 design/setup 是否存在、Transient 类型、三个不重复 winding、motion 存在、ECE 枚举和数值范围。`reviewed=false` 给出明确提示，并阻止真实 `run`。

第一版配置只接收已经展开、带单位、严格升序且包含零点的电流列表，不解析厂家的 `(步长, 次数)` 简写；写入 `.sph` 后仍是厂家接受的单值列表。验证同时给出保守规模，防止无意生成过大的二维电流×转角表。若填写真实 `Slots`，ECER 可能为齿槽转矩零电流工况调整角度区间，报告中应提示这一原生行为。

### 4. prepare

`prepare` 在输出根目录创建该设计/setup 的独立目录，复制源 `.aedt`，再次核对源哈希，并写入实际使用的配置。只允许后续代码打开这个副本，拒绝把 `prepared_project` 指回源文件，也不复制源 `.aedtresults`。

真实准备/运行时在独立 AEDT Desktop 中：打开副本并精确选择 design；核对 Transient、setup、motion 和 winding；如有需要，只在副本中把所选 winding 设为 External；生成原生 ECE3+ECER `.sph`，用 `edit_external_circuit` 载入并保存副本。

### 5. run / batch

`run` 只接受 `reviewed=true` 的配置，在自己的新 Desktop 和副本上运行所选 setup，随后调用 `ExportECEData` 到任务目录。每个返回布尔值的 PyAEDT 修改/保存/求解调用都必须检查；最终显式释放本任务 Desktop。

`batch` 接受多份独立配置，用 spawn 子进程执行，`max_parallel` 控制并发数；每项任务仍有自己的副本、Desktop、输出和核心数。Healthy 与 UD 的双任务并行 smoke 已完成，两个任务均为 `solved` 并正常关闭，耗时约 53 秒和 55 秒。旧 P3 与新任务共存时仍应依据许可证、CPU 和内存调整并发/核心预算，无需接管旧会话。

## 配置形状

实现采用一份配置对应一个设计，核心字段如下：

```json
{
  "schema": "maxwell-ece-config-v1",
  "source_project": "C:/absolute/input.aedt",
  "source_hash": "...",
  "design": "PMSM_Healthy",
  "setup": "Setup1",
  "variation": "",
  "winding_groups": ["WG_Ph1_P1", "WG_Ph2_P1", "WG_Ph3_P1"],
  "ece": {
    "current_sweeps": "0A, ...",
    "phase_angle_intervals": 2,
    "rotation_max": "...deg",
    "in_electrical_degrees": false,
    "rotation_intervals": 12,
    "skew_angle": "0deg",
    "poles": 8,
    "slots": 48,
    "output": 1,
    "resistance": "...ohm",
    "end_inductance": "...H"
  },
  "cores": 1,
  "output_dir": "C:/isolated/output",
  "reviewed": false,
  "review_notes": []
}
```

示例只说明字段形状；setup、相序、扫描、角度、对称性和输出值都必须以实际草案和用户校验为准。多设计时生成多份 JSON，再传给 `batch --max-parallel N`。

## 输出、测试与验收

### Full 360 mechanical scan

The reviewed formal candidate is `config/full360-PMSM_Healthy.json`. It uses
the original `models/aedt/E11_FULL/e11_PMSM_IPM.aedt`, `PMSM_Healthy` / `Setup1`,
`RAngM=360deg`, `EDeg=false`, and `RAngN=1440` (0.25 mechanical degree per
interval). Its seven current magnitudes are `0, 21.65, 43.3, 108.25, 216.5,
324.75, 433 A`; 433 A remains an IPeak-derived source candidate and is not a
rated-current claim. The formal output root is isolated under
`work/formal-full360-PMSM_Healthy-20261017`, so historical smoke output is not
overwritten. `Slots=0` is intentional: it disables the native zero-current
cog-refinement override while the source model's actual 48-slot geometry is
unchanged. The requested base estimate is `(2m-1)^2*(Ntheta+1) = 243529`
points. This is an estimate only; it is never used as a native progress
denominator unless a native log exposes a matching explicit counter.

`config/initial-full360-3mag-PMSM_Healthy.json` is a separate optional profile
with magnitudes `0, 216.5, 433 A`. It is marked not production validated and
does not replace the formal seven-magnitude profile.

Every prepare/live task writes `progress.json` and `timing-result.json` beside
its isolated job directory. The terminal renderer shows stage, elapsed wall
time, and ETA when a stage percentage is known. During synchronous
`analyze_setup`, a daemon tailer reads known native `logfile` paths and
`*.aedtresults` descendants. Native ECE logs commonly expose model-card and
cleanup facts but no point counter; those runs therefore show an animated
unknown-percentage bar with ETA unavailable. A percentage is displayed only
when an explicit, valid native counter is observed. Batch runs can additionally
write an aggregate progress file using `--progress-json`; each job retains its
own output/progress path and configurable `--max-parallel`, `--total-cores`,
and per-config `cores`.

Root-owned execution commands for the formal candidate are:

```powershell
$py = 'C:\Env\miniconda3\envs\pmsm\python.exe'
$cli = '.\versions\v0.3\maxwell_ece\scripts\maxwell_ece.py'
& $py $cli inspect .\models\aedt\E11_FULL\e11_PMSM_IPM.aedt --write .\versions\v0.3\maxwell_ece\config\inspection-full360.json
& $py $cli validate .\versions\v0.3\maxwell_ece\config\full360-PMSM_Healthy.json --inspection .\versions\v0.3\maxwell_ece\config\inspection-full360.json
& $py $cli prepare .\versions\v0.3\maxwell_ece\config\full360-PMSM_Healthy.json
& $py $cli run .\versions\v0.3\maxwell_ece\config\full360-PMSM_Healthy.json
```

The final `run` command is the only command in this sequence that starts
AEDT; it is intentionally owned and launched by the root agent after the
offline checks.

`ExportECEData` 官方接口只承诺写入指定目录，没有承诺固定文件名。系统样例显示 Twin Builder 可消费的主要产物为 `.sml`，例如 `E:\ANSYS Inc\v261\AnsysEM\Examples\Twin Builder\Applications\Motor Equivalent Circuit Toolkit\ECER_Model1.sml`。实现不得硬编码该文件名，而应收集本次导出目录的完整文件清单。

离线测试覆盖：多设计选择、保守 AEDT 文本解析、配置校验、已展开 sweep 列表、源哈希漂移、`.sph` 内容、路径隔离、fake `edit_external_circuit`/`ExportECEData` 调用形状和 batch 并发。离线通过只证明编排逻辑，不证明 AEDT 已完成 ECE；本轮真实证据另记录于 `logresearch/live-parallel-20261015.log` 及相应输出目录。

首个实际 smoke test 使用用户确认后的最小扫描配置和输入工程副本。单任务只有同时满足以下条件才可标记完成：

1. 源工程哈希前后不变，所有写入位于任务目录；
2. live 核对的 design、Transient、setup、motion 和三相 winding 与配置一致；
3. 原生 ECE 求解无异常；
4. `ExportECEData` 无异常，导出目录至少有一个非空且基本结构可识别的 `.sml`；
5. 记录配置、`.sph`、工程副本、导出文件及日志清单；
6. 本任务 Desktop 已释放，既有 P3 会话仍保持原状态。

许可证、资源或用户尚未确认正式参数时记录为 `blocked`，不得把正式精度结论写成 passed。多任务并行验收已证明各任务使用不同工程副本、Desktop 和输出目录，任一任务失败不会污染其他任务。当前 smoke 的 `0A, 1A`、`rot_ang_intervals=3`、`slots=0` 仅用于链路验收，不是 production 精度配置。

真实 smoke 还确认了以下运行事实和修复：关闭 `EnableTranTranLinkWithSimplorer` 后可稳定执行原生 ECE；空 variation 使用 `GetNominalVariation()`；求解后显式 `save_project()` 可保留导出所需状态；AEDT 2026 R1 的 `.sml` 头为行首 `MODELDEF ECE_Model1_ECER`，旧版 `SMLDEF` 仍兼容；`slots=0` 可关闭 cog refinement 并用于低成本 smoke。Ground 对照的有无不改变导出结果，且没有增加 pin。Twin Builder 原生导入的组件 pin 为 `A0 X0 B0 Y0 C0 Z0 ROT1 ROT2`，诊断为 0 errors。若同一 Twin Builder 工程导入 Healthy 与 UD，必须为两份配置设置不同的 `ece.device_name`，避免默认 `ECE_Model1_ECER` 重名。

## 实施顺序

1. 完成 `inspect/draft/validate/prepare` 和离线测试；
2. 完成原生 `.sph`、PyAEDT run/export 窄适配层和 fake 测试；
3. 完成 `batch --max-parallel` 的独立进程调度；
4. 把用户输入工程的实际草案交给用户校验；
5. 在用户授权和资源预算下执行单任务 smoke；（已完成）
6. 单任务通过后再做多设计串行与受资源预算的并行验收。（已完成）
7. 由用户复核正式精度扫描参数后，再运行 production 配置并记录收敛与物理拟合证据。

当前实现已通过真实 smoke 的 Maxwell 求解、导出、保存和 Twin Builder 导入链路；后续工作是正式参数复核及 production 精度验证，不新增审批门禁。
