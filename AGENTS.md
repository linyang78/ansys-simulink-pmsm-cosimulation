# AGENTS.md — thincoder-pmsm Project Guide

## Project Overview

PMSM（永磁同步电机）多域联合仿真自动化平台（2026-08 从头启动，新环境）：

**Motor-CAD(快速建模) → AEDT Maxwell 2D/3D(FEM 求解) → Twin Builder(Simplorer) 驱动电路 → MATLAB Simulink(FOC+SVPWM 闭环)**
Python 全流程自动化，实现建模仿真、闭环控制、故障注入（电气/电磁/机械/传感器四类）。

⚠️ **关键约束（用户明确要求）**：故障样机（偏心/局部退磁/磁钢碎裂等破坏对称性的场景）必须用 **Full Machine（360° 完整模型）**。
Motor-CAD 导出 Maxwell 脚本前须设置 Model Size = Full Machine（.mot 条目 `MagneticSymmetry=1`，导出脚本 `SymmetryFactor=1`）。
该设置是 Motor-CAD GUI 内部状态，脚本 set 后保存会被内部状态覆盖 → 加载用户调好的 full 模板 `models/motorcad/e11_User.mot` 再 `load_from_file` + `export_to_ansys_electronics_desktop()`。

本项目所有结论以本环境实测为准。

## Tech Stack（2026-08-17/18 实测）

| 组件 | 版本 | 位置 / 说明 |
| --- | --- | --- |
| conda 环境 | **`pmsm`**，Python 3.12.13 | `C:\Env\miniconda3\envs\pmsm`；所有命令用 `C:\Env\miniconda3\envs\pmsm\python.exe` |
| ansys-motorcad-core | **0.8.8** | 导入 `ansys.motorcad.core`，类 `MotorCAD`（`import motorcad` 会 ImportError） |
| pyaedt | **1.4.0** | 导入 `ansys.aedt.core`（1.x 命名空间，`Maxwell2d`/`TwinBuilder` 已实测可导入） |
| ansys-aedt-mcp | **0.2.dev0** | 官方 MCP server（gRPC 连 AEDT）；CLI `python -m ansys.aedt.mcp`；**19 个工具**（2026-09-14 实连复测，含 run_python_script/run_python_code/analyze_design/export_results）；挂载按宿主：CLI 读项目根 `.mcp.json`，VS Code 扩展只读全局 `config.json` 的 `mcp.servers`（2026-09-14 实测）；会话内工具名 `pyaedt-mcp_*`（配置与启用判据见 `help/environment.md` §5） |
| matlabengine | 24.2 | 配对 MATLAB R2024b；导入 `matlab.engine` |
| AEDT | 2026 R1 (v261) | `E:\ANSYS Inc\v261\AnsysEM\ansysedt.exe`；含 Maxwell 2D/3D、Twin Builder、`MaxwellSimulink.dll` |
| Motor-CAD | 2026R1 | `E:\ANSYS Inc\v261\motorcad\MotorCAD.exe`；同目录有 `Motor-CAD.chm`/`Tutorials/`/`Python/` |
| MATLAB | R2024b | `E:\Program Files\MATLAB\R2024b`；MEX 默认 MSVC 2022 |
| 许可 | 1055@localhost | `ANSYSLMD_LICENSE_FILE`；M0 三工具实机启动均成功（间接确认） |
| matlab-agentic-toolkit | GitHub main | 已克隆 `help/repos/matlab-agentic-toolkit/` |

完整环境清单：`help/environment.md`。

## Common Commands

```pwsh
# 统一解释器（conda activate pmsm 等效）
& 'C:\Env\miniconda3\envs\pmsm\python.exe' -V

# AEDT MCP server（手工起；会话内由项目根 .mcp.json 自动挂载，无需手跑）
# --connect 需 AEDT 已起 gRPC，且会锁定连接并禁用 launch/connect/disconnect 三工具——会话配置刻意不加
& 'C:\Env\miniconda3\envs\pmsm\python.exe' -m ansys.aedt.mcp --transport stdio

# 会话内 MCP 工具（新开会话生效，名形如 pyaedt-mcp_<tool>）：
# pyaedt-mcp_check_aedt_status / pyaedt-mcp_launch_aedt / pyaedt-mcp_connect_to_aedt / pyaedt-mcp_run_python_code 等

# 测试（脚本落地后）
& 'C:\Env\miniconda3\envs\pmsm\python.exe' -m pytest tests/ -q
```

**本机 shell 注意**：cmd 中文编码乱码（GBK 显示错位）；复杂逻辑用 node/python 脚本文件，避免 shell 拼接与重定向。GitHub 网络可用（已实测克隆）。

## Directory Layout

```
thincoder-pmsm/
├── AGENTS.md                    # 本文件
├── .mcp.json                    # ThinCoder MCP 配置（pyaedt-mcp → pmsm env，stdio）
├── help/                        # 资料库（索引见 help/README.md）
│   ├── environment.md           #   本机环境清单（随检测结果更新）
│   ├── repos/                   #   GitHub 克隆：pymotorcad / pyaedt-mcp / matlab-agentic-toolkit
│   ├── docs/                    #   在线 API 文档快照（motorcad/aedt 索引）
│   ├── ansys-help-topics/       #   Ansys 官方帮助 25 主题（脚本指南/联合仿真教程/组件库）
│   └── legacy-simulation_workflow/  # 旧项目归档（仅参考，结论需回归）
├── models/
│   └── motorcad/
│       ├── e11_User.mot         # ★ Full Machine 状态模板（故障样机导出用）
│       └── e11_User/            #   MessageLogs（运行日志）
└── (规划) src/ scripts/ config/ tests/ results/ templates/
```

规划目录：`src/{motorcad_controller,aedt_controller,simulink_controller,data_exchange}/`、`scripts/`（check_env.py / run_m1..m6.py）、`config/{base,cases}.yaml`、`tests/`、`results/<batch>/` 归档。

## Architecture Notes

### 链路与里程碑（本项目从 M0 开始，逐步实测推进）

```
M0 环境检测 ✅ (2026-08-18) → M1 Motor-CAD 快速建模 → M2 Maxwell 电磁建模 → M3 TB 电路搭建
                  → M4 Simulink 控制耦合 → M5 故障注入(场景矩阵) → M6 批量运行+报告
```

**M0 结论（2026-08-18 实测，详见 help/environment.md §5）**：
- **pyaedt-mcp 全链路通**：launch_aedt（Maxwell2d gRPC 36357）✅、独立 MCP server（HTTP）✅、--connect 发现本机常驻 gRPC 会话（端口 50051 / PID 43448）✅、run_python_code 执行+result 回传 ✅、19 工具清单确认（2026-09-14 复核：该常驻会话已不在、当前无 `ansysedt` 进程；现行挂载与启用判据见 `help/environment.md` §5）
- Motor-CAD 实例 10.9s 启动 ✅，`e11_User.mot` 加载 ✅，**`MagneticSymmetry=1`（full 状态实测确认）**，但 `MagneticSymmetryFactor=8` → M1 导出时验证脚本 SymmetryFactor
- MATLAB Engine 6.8s 启动 ✅，R2024b 执行 ✅

### 联合仿真三方案（设计取向，B 为主线）

| 方案 | 方式 | 适用 |
| --- | --- | --- |
| A 全耦合 | Maxwell FEM ↔ TB 电路 ↔ Simulink 三方实时 | 关键工况、故障机理验证 |
| **B 两步法（推荐）** | 先离线导出等效模型/ROM（dq 磁链图/电感/反电动势，数据源 Motor-CAD 或 Maxwell），TB 用等效电机模型再与 Simulink 耦合 | 故障批量扫描、控制策略验证 |
| C 离线数据链 | 各工具独立运行，文件（CSV/MAT）传递，Simulink 查表 | 参数初筛、回归测试 |

### 故障注入矩阵（设计）

| 类别 | 故障 | 注入层级 | 实现 |
| --- | --- | --- | --- |
| 电气 | 断相/相间短路/匝间短路/对地短路/IGBT 开路短路 | TB 电路 | 预置故障支路+可控开关，`t_fault` 动作；匝间短路=绕组分段（90%+10%）+短路电阻旁路 |
| 电磁 | 整体/局部退磁 | Maxwell 材料 | 参数化 `Br`/`Hc`（整体）；磁体分区改局部材料（局部） |
| 电磁 | 静/动偏心、磁钢碎裂/错位 | Maxwell 几何 | 偏移参数化；磁体分段移除/偏移（需 Full Machine！） |
| 机械 | 负载突变/堵转、轴承摩擦 | Simulink | 负载阶跃/斜坡/常值；摩擦系数 |
| 传感器 | 位置/电流传感器故障 | Simulink | 信号通道增益偏差/偏置/噪声/饱和 |

### 历史参考经验（旧环境结论，仅参考，本项目须实测回归）

旧项目（pyaedt 1.2.0 / motorcad-core 0.8.6 / py3.11）归档于 `help/legacy-simulation_workflow/AGENTS.md`，要点：
- Motor-CAD：`load_from_file` 需绝对路径；导出产物扩展名强制 .py；参数化用 datastore 的 activex 名；Full Machine 由 `MagneticSymmetry=1` 决定且 set_variable 改不了
- AEDT：脚本执行用 `ansysedt.exe -RunScriptAndExit <script> [-Batch]`；`AnsysAirgapMesh=1` 必须开；gRPC 实例 release 后残留 .lock
- TB：组件路径格式 `库\子目录:组件名`（电压源 `Sources:E`）；`CreateComponent` 返回值即 CompInst ID；地 = `CreateGround` → `GPort@0;N`
- MATLAB：MEX 编译器检测变量 `MW_MINGW64_LOC`

**待回归清单**（本环境逐项实测后才能写进本项目结论）：`ansysedt.exe -RunScriptAndExit` 通道、`AnsysAirgapMesh` 机制、`Desktop.load_project` vs `open_project`、gRPC `post.export_report_to_file`、TB 组件 API（CreateComponent/CreateWire/CreateGround）。已实测：`MagneticSymmetry=1` 存在于 .mot（读取层面确认）。

## Coding Conventions

- Python 3.10+ 类型注解（`str | Path`、`list[str]`）；模块 docstring 注明对应里程碑/文档章节
- 控制器在 `src/`，入口脚本在 `scripts/`，配置在 `config/{base,cases}.yaml`，测试在 `tests/`
- 新增代码必须配套 pytest 单测；完成后 `lint full=true` + `verify`
- 实验/探针脚本命名 `_xxx.py`，完成后清理，勿提交
- 中文注释与日志（项目内中文为主）
- 本机 shell 一律用 pwsh 或 node/python 脚本；cmd 中文乱码，bash 双引号内 `$_` 会被吞
- 提交前检查：勿把临时文件/日志/生成物（models/ results/ 产物）打包进 commit
- 里程碑状态同步更新 AGENTS.md 与本项目文档

## 工作约定（资料/环境）

- 新增资料放 `help/` 对应子目录并在 `help/README.md` 登记；在线文档快照标注日期+URL
- 环境版本/路径/检测结果有变化时更新 `help/environment.md` 与本文 Tech Stack 表
- 旧项目资料只读参考（`help/legacy-simulation_workflow/`），结论使用前须回归
- Motor-CAD 相关操作优先查：`help/ansys-help-topics/Ansys_Maxwell_Export/`（导出文档）、`help/repos/pymotorcad/examples/`
- AEDT/TB 相关操作优先查：`help/ansys-help-topics/` 下各脚本指南与教程
