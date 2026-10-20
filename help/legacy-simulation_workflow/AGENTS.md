# AGENTS.md — simulation_workflow Project Guide

## Project Overview

PMSM 多域联合仿真自动化平台(见 `readme.md` 完整技术方案):

**Motor-CAD(快速建模) → Maxwell 2D(FEM 求解) → Twin Builder 电路 → Simulink 控制**,Python 全流程自动化,支持 PMSM 故障注入(断相/匝间短路/退磁等)。

里程碑状态(详见 readme §9):
- **M0 环境就绪** ✅ 2026-08-04 门禁全绿(exit 0)
- **M1 Motor-CAD 快速建模** ✅ 2026-08-04 实机跑通(加载→参数化→EMag→导出 full 脚本→归档)
- **M2 Maxwell 2D 建模** ✅ 2026-08-07 实机跑通(CLI 执行脚本→求解→报告 CSV→归档)
- **M3 TB 电路** 🚧 进行中:组件放置/引脚定位/连线脚本 API 已打通,最小电路(V+R+GND)求解尚在收尾
- M4 Simulink 耦合 / M5 故障注入矩阵 / M6 报告:待办

## Tech Stack

- Python **3.11.15**,conda 环境 **`C:\Env\anaconda3\envs\pyaedt`**(所有命令用该解释器)
- Motor-CAD **2026R1**;`ansys-motorcad-core` **0.8.6**(导入名 `ansys.motorcad.core`,类名 **`MotorCAD`**;`import motorcad` 会 ImportError)
- AEDT **2026 R1**(`F:\ANSYS Inc\v261\AnsysEM`);`pyaedt` **1.2.0**(导入名 `ansys.aedt.core`)
- MATLAB **R2024b** + matlabengine 24.2;MEX 编译器 MSVC 2022(MinGW64 为备选)
- 许可 1055@localhost;环境变量 `ANSYSEM_ROOT261`/`AWP_ROOT261`/`SIMPLORER_HOME`/`MOTORCAD_ACTIVEX` 已配置

## Common Commands

```pwsh
# 环境门禁(实机启动三工具 + MEX 实测编译)
& 'C:\Env\anaconda3\envs\pyaedt\python.exe' scripts/check_env.py            # full 模式(默认)
& 'C:\Env\anaconda3\envs\pyaedt\python.exe' scripts/check_env.py --mode imports --skip aedt,motorcad,matlab

# 里程碑入口
& 'C:\Env\anaconda3\envs\pyaedt\python.exe' scripts/run_m1.py [--skip-emag] [--strict-params] [--batch <名>]
& 'C:\Env\anaconda3\envs\pyaedt\python.exe' scripts/run_m2.py [--visible] [--batch <名>]

# 测试
& 'C:\Env\anaconda3\envs\pyaedt\python.exe' -m pytest tests/ -q
```

**本机所有 shell 必须用 pwsh**(`pwsh -NoProfile -Command "..."`);bash 双引号内 `$_` 会被吞,复杂逻辑用 node/python 脚本文件代替 shell 拼接。

## Coding Conventions

- Python 3.10+ 类型注解(`str | Path`、`list[str]`);模块 docstring 注明对应 readme 章节
- 控制器在 `src/{motorcad_controller,aedt_controller}/`,入口脚本在 `scripts/`,配置在 `config/{base,cases}.yaml`,测试在 `tests/`
- 新增代码必须配套 pytest 单测;完成后 `lint full=true` + `verify`
- 实验/探针脚本命名 `_xxx.py`,完成后清理,勿提交
- 中文注释与日志(项目内中文为主)

## Architecture Notes

### 目录与数据流

```
config/cases.yaml(电机参数/场景) → scripts/run_m1.py → src/motorcad_controller/
  → 导出脚本 models/maxwell/e11_bpm.py → scripts/run_m2.py → src/aedt_controller/
  → 报告 CSV → results/maxwell/<batch>/(归档:工程+CSV+脚本+日志+metadata.json)
```

- `help_md/`:26 个 Ansys 官方帮助主题(**实施前优先查**,含 TB 脚本指南/Basic Elements 组件库等)
- `templates/motorcad/`:手工模板入库;`models/motorcad/`:e11_User.mot(**full 状态**)与导出脚本入库
- `results/`、`batch.log`、`models/` 生成物 gitignore

### 关键实测结论(代码不得偏离)

**Motor-CAD 侧**:
- `load_from_file` 接受 .mtt/.mot;**所有路径必须绝对路径**(进程不解析相对路径)
- `export_to_ansys_electronics_desktop` 产出 .py 脚本(扩展名被强制),含建模→报告→AnalyzeAll→SaveAs
- Full Machine 由 `.mot` 条目 `MagneticSymmetry=1` 决定;`set_variable` 无法改它(GUI 内部状态),直接用用户调好的 full 模型
- 参数化用 datastore 的 activex 名(如 `PeakCurrent`/`PhaseAdvance`/`Magnet_Br_Multiplier`);`AnsysAirgapMesh` 是普通 settings 变量,set 后内存生效
- 导出脚本内容依赖 Motor-CAD 会话状态(激励参数 Vpeak/Rphase 等取当前计算值)

**AEDT/Maxwell 侧**:
- **脚本执行唯一可靠通道**:命令行 `ansysedt.exe -RunScriptAndExit <script> [-Batch]`(pyaedt COM IDispatch 有怪癖、gRPC 无 ExecuteScript)
- `AnsysAirgapMesh=1`(气隙圆柱网格)**必须开**,否则求解报 "Edge is not preserved in the mesh";已在 cases.yaml `export.airgap_cylindrical_mesh` 固化,run_m1 导出前自动设置
- M1 脚本的报告在 AnalyzeAll **之前**创建,求解后是空壳(ExportToFile 报 no data);导出前须**重解 + 重建报告**(`export_reports_to_csv` 从 M1 脚本提取 CreateReport 块,括号配平)再导出
- pyaedt gRPC 实例 release 后进程残留并持 .lock(导致 OpenProject 失败)——M2 全程 CLI 规避;残留实例需 kill + 删锁
- pyaedt 1.2.0:`Desktop.load_project`(不是 open_project)、`design_list()`/`active_design()` 是方法;gRPC 下 `post.export_report_to_file` 静默不产文件

**Twin Builder(M3,实测中)**:
- 组件库在 `F:\ANSYS Inc\v261\AnsysEM\syslib\Simplorer Elements\`;组件路径格式 `库\子目录:组件名`(电压源是 `Sources:E` 不是 V!;电阻 `Passive Elements:R`;理想开关 `Ideal Switches:S`;库枚举用 `oProject.GetDefinitionManager().GetManager("Component").GetLibContents(<.aclb 绝对路径>)`)
- 放置 `oEditor.CreateComponent([...], ["NAME:Attributes", ...])` **返回值即 CompInst ID**(`CompInst@R;2;3` 格式),不要自己猜 ID
- 引脚:`SelectElement` 选中(需 CompInst ID)→ `GetComponentPins` → `GetComponentPinLocation(id, pin, True/False)` 拿**绝对坐标**
- 连线 `oEditor.CreateWire(params, attrs)` 必须两个参数;端点须精确落在引脚坐标上
- 地 = `CreateGround` → `GPort@0;N`(GlobalPort,全局节点 '0'),**无引脚 API**;连接点 = 放置点 + (0, 0.00254)(ground_earth 符号 PinDef 偏移)——当前卡点:wire 到 GPort 的连接尚未吸附成功(见 M3 实验 _tb_exp*.py)
- 瞬态设置 `oDesign.GetModule("SimSetup")`;默认 setup 名为 'TR',文件里 `TransientData(停止, HMax, HInit, false, '')`
- ID 冲突:传 "Id:=" 会被 AEDT 忽略并警告,一律用返回值

### 工作约定

- 提交前:`git rm --cached _commit_msg.txt` 或先删提交信息文件,勿把临时文件打包进 commit
- 里程碑状态同步更新 readme §9 表格与 docs/ 验证报告
