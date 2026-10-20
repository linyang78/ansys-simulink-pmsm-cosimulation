# help/ —— 项目资料库

PMSM 联合仿真项目（Motor-CAD → AEDT Maxwell → Twin Builder → Simulink）的参考资料索引。
建库时间：2026-08-17。测试环境用资料都在这，先看本文件再动手。

## 目录总览

```
help/
├── README.md                         ← 本文件（索引）
├── environment.md                    ← 本机环境清单（2026-08-17 实测）
├── repos/                            ← GitHub 仓库克隆（shallow；本目录被 .gitignore 忽略，不纳入版本库）
│   ├── pymotorcad/                   ← ansys/pymotorcad main(0.9.dev0)；examples/ + samples/ + tests/ 示例齐全
│   │   └─ https://github.com/ansys/pymotorcad.git
│   ├── pyaedt-mcp/                   ← ansys/pyaedt-mcp main(0.1.dev0)；官方 MCP server 源码+文档
│   │   └─ https://github.com/ansys/pyaedt-mcp.git
│   └── matlab-agentic-toolkit/       ← matlab/matlab-agentic-toolkit；MATLAB agent 插件
│       └─ https://github.com/matlab/matlab-agentic-toolkit.git
├── docs/                             ← 在线 API 文档快照
│   ├── motorcad_methods_index.md     ← PyMotorCAD API 索引 + 常用方法速查
│   ├── motorcad_samples_index.md     ← PyMotorCAD 示例索引（本地示例位置）
│   └── aedt_api_index.md             ← PyAEDT API 索引 + 本项目相关 App/模块
├── ansys-help-topics/                ← Ansys 官方帮助主题（25 个，66.8MB，来自前身项目整理）
│   ├── Maxwell/  Circuit/  Twin Builder/  Basic Elements/  Power System/   （大主题，md 单页）
│   ├── MaxwellScriptingGuide/  CircuitScriptingGuide/  Twin BuilderScriptingGuide/  （脚本指南）
│   ├── Motor-CAD_FMU_Tutorial/       ← Motor-CAD FMU ↔ Twin Builder/Simulink 联合仿真教程（含图）
│   ├── TwinBuilder_ECE_Tutorial/     ← ECE 等效电路导出教程
│   ├── Simplorer_BLACMotorControlSystem/  ← Simplorer 电机控制系统示例
│   ├── Simplorer_WaterPumpingSystem/
│   ├── MATLAB_Simscape_Export_BPM/   ← Simscape 导出教程
│   ├── Ansys_Maxwell_Export/         ← Motor-CAD → Maxwell 导出文档（关键！）
│   ├── TwinBuilder_Thermal_Network_Export/
│   ├── New Simplorer EV_HEV Library/
│   ├── Twin Builder Getting Started Guide/
│   ├── BPM_Electromagnetic_Model/  BPM_Modelling/  Design Methodology for Interior PM Motors/
│   ├── Maxwell Transient Problem/  Maxwell Designing a Rotational Actuator/  Maxwell 2D Magnetostatic Solenoid Problem/
│   ├── Ansys_Maxwell_HairpinWindings_Export/
│   └── Running_Parallel_Sessions_Scripting/
└── legacy-simulation_workflow/       ← 前身项目归档（F:\project\simulation_workflow）
    ├── readme.md                     ← 完整技术方案（架构/拓扑/故障注入矩阵/路线图）
    ├── AGENTS.md                     ← 前身实测结论（M0-M3 踩坑记录，重点读）
    ├── config/base.yaml              ← 全局配置参考（路径/版本/许可/超时）
    ├── config/cases.yaml             ← 场景矩阵配置参考
    └── docs/                         ← MCP 用法 + M0/M1/M2 验证报告
```

## 使用指引

| 需求 | 看哪里 |
| --- | --- |
| Motor-CAD 脚本 API | `repos/pymotorcad/examples/` + `repos/pymotorcad/samples/` + `docs/motorcad_methods_index.md` |
| Motor-CAD → Maxwell 导出 | `ansys-help-topics/Ansys_Maxwell_Export/` + `Motor-CAD_FMU_Tutorial/` |
| 导出 full machine 约束 | `environment.md` §Motor-CAD、`legacy-simulation_workflow/AGENTS.md`（MagneticSymmetry 机制） |
| AEDT/Maxwell 脚本 | `ansys-help-topics/MaxwellScriptingGuide/` + `Maxwell/` + `docs/aedt_api_index.md` |
| Twin Builder 电路脚本 | `ansys-help-topics/Twin BuilderScriptingGuide/` + `Twin Builder/` + `Basic Elements/`（组件库） |
| TB ↔ Simulink 联合仿真 | `ansys-help-topics/Motor-CAD_FMU_Tutorial/`（FMU 路线）+ `TwinBuilder_ECE_Tutorial/`（ECE 路线） |
| Simulink 自动化 | `repos/matlab-agentic-toolkit/README.md` + `legacy-simulation_workflow/docs/aedt-mcp-usage.md` |
| AEDT MCP（gRPC） | `repos/pyaedt-mcp/`（doc/ + README）+ `legacy-simulation_workflow/docs/aedt-mcp-usage.md` |
| 环境/版本/许可 | `environment.md` |
| 整体架构/路线图 | `legacy-simulation_workflow/readme.md` |

## 维护约定

- 新下载的资料放对应子目录，并在本 README 更新一行索引
- 抓取在线文档：存 `docs/`，标注快照日期与来源 URL
- 前身项目的资料只进 `legacy-simulation_workflow/`，不改动原文件（原项目在 F:\project\simulation_workflow）
