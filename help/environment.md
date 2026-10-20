# 本机环境清单（2026-08-17 实测；2026-09-14 更新 §5 MCP 配置段）

> 实测方式：本会话自动探查（conda/pip/注册表/文件系统/import 验证）。前身项目 M0 记录以「旧 M0」标注。

## 1. Python / conda

| 项 | 值 |
| --- | --- |
| conda 根 | `C:\Env\miniconda3`（miniconda） |
| 虚拟环境 | **`pmsm`** → `C:\Env\miniconda3\envs\pmsm` |
| Python | **3.12.13**（conda-forge） |
| 解释器调用 | `C:\Env\miniconda3\envs\pmsm\python.exe` |
| 其他环境 | `pytorch`（与本项目无关） |

**pmsm 环境关键包（pip list 实测）**：

| 包 | 版本 | 说明 / 导入名 |
| --- | --- | --- |
| ansys-motorcad-core | **0.8.8** | 导入 `ansys.motorcad.core`，类 `MotorCAD`；0.8.x 新增 `ansys.motorcad.core.geometry*`（Adaptive Templates 几何） |
| pyaedt | **1.4.0** | 导入 `ansys.aedt.core`（1.x 新命名空间，`Maxwell2d`/`TwinBuilder` import 实测 ok） |
| ansys-aedt-mcp | **0.2.dev0** | 官方 MCP server；CLI：`python -m ansys.aedt.mcp --transport stdio\|http --machine --port --version --connect`（默认 gRPC 50051，non-graphical） |
| ansys-common-mcp | 0.3.3 | MCP 公共库 |
| matlabengine | **24.2** | 导入 `matlab.engine` ok；配对 MATLAB R2024b |
| pyedb | 0.81.0 | EDB 相关（PCB，备用） |
| 其他 | numpy 2.5.2 / pyvista 0.48.4 / vtk 9.6.2 / meshio 5.3.5 / pywinauto 0.6.9 / comtypes 1.4.16 / pywin32 312 / matplotlib 3.11.1 / pytest 9.1.1 / fastmcp 3.4.7 / mcp 1.29.0 | |

## 2. Ansys 软件（2026 R1）

| 软件 | 路径 | 说明 |
| --- | --- | --- |
| AEDT 2026 R1 (v261) | `E:\ANSYS Inc\v261\AnsysEM\ansysedt.exe` | 2026.1.0；含 Maxwell 2D/3D、Twin Builder(Simplorer)、`MaxwellSimulink.dll`（Simulink 耦合）、`DigitalTwinFitting.dll`（ROM） |
| Motor-CAD 2026R1 | `E:\ANSYS Inc\v261\motorcad\MotorCAD.exe` | 2026.1.1；并入 ANSYS 26.1 目录；同目录含 `Motor-CAD.chm`（官方帮助）、`Tutorials/`、`Python/`、`FMU/` |
| 安装包 | 未核实（重装系统前的 `D:\仿真软件安装包\ANSYS2026R1\` 未复查） | 重装/补组件前先确认安装包位置 |
| 许可 | `1055@localhost`（ANSYSLMD_LICENSE_FILE，2026-10-20 实测） | PLE Licensing 2026 R1 服务运行中 |

环境变量（旧 M0 记录，未重测）：`ANSYSEM_ROOT261`、`AWP_ROOT261`、`SIMPLORER_HOME`、`MOTORCAD_ACTIVEX` 已配置；`ANSYS261_DIR` 指向不存在目录（遗留变量，无影响）。

## 3. MATLAB

| 项 | 值 |
| --- | --- |
| 安装 | `E:\Program Files\MATLAB\R2024b`（R2024b = 24.2） |
| matlabengine | 已装 24.2（导入 ok） |
| MEX 编译器 | 默认 **MSVC 2022**（官方支持）；MinGW64 `F:\Env\mingw64` 已不存在，如改用 MinGW 需重装并设 `MW_MINGW64_LOC` |
| 联合仿真 | TB 的 Simulink Co-Simulation 组件生成 S-function（MEX），版本强相关，M0 需重验证 |
| matlab-agentic-toolkit | GitHub 仓库已克隆 `help/repos/matlab-agentic-toolkit/`，用法见其 README |

## 4. 前身项目（继承参考）

- **`F:\project\simulation_workflow`**（git 仓库）：M0 ✅ / M1 ✅ / M2 ✅ / M3 🚧（TB 最小电路 wire→GPort 吸附未通）；技术方案与实测结论已归档到 `help/legacy-simulation_workflow/`
- 版本差异：前身 env `pyaedt`（py3.11.15 + pyaedt 1.2.0 + motorcad-core 0.8.6）；现 env `pmsm`（py3.12.13 + pyaedt 1.4.0 + motorcad-core 0.8.8）—— **旧结论需回归验证**
- 用户外部资料（未拷贝，参考用）：
  - `F:\simulink\开源-永磁同步电机直连控制资料\`（Simulink 程序/论文/电机参数/FOC 学习资料/硬件）
  - `F:\simulink\开题建模仿真\`（用户自己的 *.aedt 工程：PMSM MAGSTATIC1 等）
  - `F:\simulink\model\Synchronous Generator.aedt`

## 5. 环境门禁检测（2026-08-18 实机，M0）

**thincoder MCP 配置（现行，2026-10-20 实连复核）**：项目根 `E:\Vscode\thincoder-pmsm\.mcp.json` 挂载服务器 `pyaedt-mcp`，命令 = `C:\Env\miniconda3\envs\pmsm\python.exe -m ansys.aedt.mcp --transport stdio`。

- 挂载机制（两宿主不同，2026-09-14 实证）：**CLI**（全局 npm 包 thincoder 0.12.62）建会话时读项目根 `.mcp.json`（`mcpServers` 对象形态）并与全局 `~/.thincoder/config.json` 的 `mcp.servers` 合并（同名以全局优先），只在启动时读取；**VS Code 扩展**（xinbo-tech.thincoder-vscode 0.9.2，自带独立副本）**只读全局 `config.json` 的 `mcp.servers`，不读项目 `.mcp.json`**（源码 `src/extension/panel-chat.mjs:401` → `src/config-mcp.mjs`；全扩展文件检索无 `.mcp.json` 支持）——要让 VS Code 会话也带上工具，须把同一条目加进全局 `config.json`（VS Code 设置面板 MCP 段添加，或直接编辑该文件）。
- 刻意不加 `--connect`：该开关启动即锁定连接并禁用 `launch_aedt`/`connect_to_aedt`/`disconnect_from_aedt`（源码 `ansys/aedt/mcp/tools.py:1673-1675`）——会话配置改为按需连接，19 工具全量可用。
- 背景（M0，2026-08-18）：曾写在全局 `config.json` 的 `mcp.servers[0]`（备份 `config.json.bak-2026-08-17T16-51-15`）；曾用 `--dynamic-tool-discovery` 导致未连接时工具只剩 5 个，已弃用。该全局条目现已不在（2026-09-14 复核：全局 config.json 无 `mcp` 段），改由项目级 `.mcp.json` 承载（项目范围、不受全局配置重写影响）。
- 实测（2026-09-14）：文件 291 字节、无 BOM、JSON 解析通过；用 ThinCoder `connectMcpServer` 实连 → **19 个工具**（约 4.2s），工具名形如 `pyaedt-mcp_<tool>`。
- 启用判据（三层）：① 会话工具表出现 `pyaedt-mcp_*` 工具；TUI `/mcp list` 显示「已连接 + 工具数」、`/mcp test pyaedt-mcp` 一次性探活；② 手工起服务看 stderr 两行 `Starting MCP server 'PyAEDT-MCP' with transport 'stdio'` + `Persistent Python session started successfully`；③ `pyaedt-mcp_check_aedt_status` / `pyaedt-mcp_get_pyaedt_logs` 判断 AEDT 侧状态。
- 注意：2026-09-14 复核本机无 `ansysedt` 进程——M0 记录的常驻 gRPC 会话（端口 50051 / PID 43448）已不在；用前 `launch_aedt`，或手工 `ansysedt.exe -grpcsrv 50051`。

**pyaedt-mcp（重点，全链路实测通过）**：

| 检测项 | 结果 |
| --- | --- |
| `check_aedt_installed` | AEDT 2026.1 + 2026.1AWP 已装（`E:\ANSYS Inc\v261\AnsysEM`，2026-10-20 路径复核） |
| `launch_aedt`（Maxwell2d, non-graphical, gRPC） | ✅ 5.4s 启动，自动建 Project7 + Maxwell 2D 设计；端口 36357（会话 PID 54256） |
| 独立 MCP server（HTTP transport） | ✅ `python -m ansys.aedt.mcp --transport http --port <p>`，initialize 200，serverInfo PyAEDT-MCP v3.4.7 |
| `--connect` 自动发现已有 gRPC | ✅ 发现并连上本机常驻 gRPC 会话（**端口 50051，PID 43448**，空工程；来源待确认，勿删） |
| `run_python_code` 执行 | ✅ `result='PING_OK pyaedt=1.4.0'` 回传成功 |
| 完整工具面 | **19 个工具**：check/launch/connect/disconnect + `run_python_script`/`run_python_code` + list_projects/list_designs/open/save/create_design + analyze_design + export_results/screenshot/export_config/get_model_info/clear_aedt |
| 会话工具通道 | M0 会话当时：工具表自带 pyaedt-mcp_*，可随时 check/launch/connect（现行挂载方式见本节上方 2026-09-14 段） |

**Motor-CAD（实机连接）**：✅ 10.9s 启动实例（0.8.8）；`load_from_file(e11_User.mot)` OK；datastore 13969 条；**`MagneticSymmetry=1`（full 状态确认）**；注意 `MagneticSymmetryFactor` 仍=8（M1 导出时需验证脚本 SymmetryFactor）；quit 干净。

**MATLAB Engine**：✅ 6.8s 启动，`version()=24.2.0.2712019 (R2024b)`，sqrt 执行 OK，quit 干净。

**许可**：三工具均能启动 → PLE Licensing 正常（间接确认）。

import 级快测（2026-08-17）：`from ansys.aedt.core import Maxwell2d, TwinBuilder` ✅ / `import ansys.motorcad.core` 0.8.8 ✅ / `import matlab.engine` ✅ / MCP CLI `--help` ✅。

待 M1/M2 再回归：`ansysedt.exe -RunScriptAndExit` 通道、`AnsysAirgapMesh`、`Desktop.load_project`、gRPC `export_report_to_file`、TB 组件 API。
