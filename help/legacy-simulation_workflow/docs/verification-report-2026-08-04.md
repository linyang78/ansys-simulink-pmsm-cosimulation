# readme.md 技术方案检验报告

- **检验日期**:2026-08-04(实测复验)
- **检验对象**:`readme.md`(PMSM 多域联合仿真自动化平台 — 技术方案)
- **检验方式**:环境实机复测(Motor-CAD / MATLAB / AEDT 真实启动)+ 已装 Python 包 API 逐条核对 + 仓库现状比对
- **原始证据**:`docs/m0_live_report_2026-08-04.json`(M0 实机启动结果)

---

## 1. 结论摘要

| 维度 | 结论 |
| --- | --- |
| 方案技术路线(架构/拓扑/故障注入) | ✅ **可行**,分层清晰、主线(方案 B)选择合理 |
| 环境就绪度(readme §3 声明) | ✅ **基本全部属实**,实测三大工具均可真实启动 |
| 附录 API 速查(§11) | ⚠️ **1 处硬错误 + 4 处方法名偏差**,见 §4 |
| readme "已实现" 声明(M0/M1) | ❌ **仓库中无任何代码/产物物证**,见 §5 |
| 主要落地风险 | TB↔Simulink 联合仿真组件自动化在 PyAEDT 无封装,需裸 COM/VBS 脚本 |

---

## 2. 环境实测(2026-08-04)

| # | 项 | readme 声明 | 实测 | 结论 |
| --- | --- | --- | --- | --- |
| E1 | conda 环境路径 | §3.1 `C:\Env\anaconda3\envs\pyaedt`;**§3.3 `C:\Users\win\.conda\envs\pyaedt`** | 实际在 `C:\Env\anaconda3\envs\pyaedt`(`C:\Users\win\.conda\envs` 不存在) | ⚠️ §3.3 路径有误,应修正为 §3.1 值 |
| E2 | Python 版本 | 3.11.15 | 3.11.15 ✓ | ✅ |
| E3 | 关键包 | pyaedt 1.2.0 / ansys-motorcad-core 0.8.6 / matlabengine 24.2 / pyyaml / pandas / numpy / matplotlib / jinja2 | pyaedt **1.2.0**、ansys-motorcad-core **0.8.6**、matlabengine **24.2**、PyYAML 6.0.3、**pandas 3.0.3**、**numpy 2.4.6**、matplotlib 3.11.0、Jinja2 3.1.6 全部在位 | ✅ 注意:numpy/pandas 为 2.x/3.x 大版本,旧示例代码需注意 API 兼容 |
| E4 | AEDT 安装 | `F:\ANSYS Inc\v261\AnsysEM` | 存在 ✓;`MaxwellSimulink.dll` ✓、`DigitalTwinFitting.dll` ✓、`SimplorerSolver.exe`/`SimplorerCOMEngine.exe` ✓ | ✅ Twin Builder 为 AEDT 内置设计类型,无独立 exe,与 2021R2+ 架构一致 |
| E5 | Motor-CAD | `F:\ANSYS Inc\v261\motorcad\MotorCAD.exe` | 存在 ✓;`MOTORCAD_ACTIVEX` 已配置 ✓ | ✅ |
| E6 | MATLAB | R2024b + Simulink 在位 | R2024b(24.2.0.2712019)✓;`license('test','Simulink')=1` ✓;`sim` 内置 ✓ | ✅ |
| E7 | MEX C 编译器 | "M0 已验证可用" | **不可用**:本机仅有 VS 18 Community(MSVC 14.51.36231),不在 MATLAB R2024b 支持列表内;`mex.getCompilerConfigurations('C','Installed')` 返回 **0 个**,`mex('-setup','-n')` 报"未检测到支持的编译器" | ❌ readme 声称不成立;需装 VS 2022 Build Tools 或 MATLAB MinGW-w64 支持包 |
| E8 | 环境变量 | ANSYSEM_ROOT261 / AWP_ROOT261 / ANSYS261_DIR / SIMPLORER_HOME / MOTORCAD_ACTIVEX / ANSYSLMD_LICENSE_FILE | 全部已设置;**但 `ANSYS261_DIR=F:\ANSYS Inc\v261\ANSYS` 指向的目录不存在**(v261 下无 `ANSYS` 子目录) | ⚠️ 疑为废弃/失效变量,不影响 pyaedt 启动(走 AWP_ROOT261),建议核实或修正 |
| E9 | 许可 | PLE 1055@localhost | 端口 1055 LISTENING ✓;实测结束后无残留 ansysedt/MotorCAD 进程 ✓ | ✅ |

### M0 实机启动复测(本报告核心动作)

| 项 | 实测结果 | 耗时 |
| --- | --- | --- |
| Motor-CAD(PyMotorCAD `MotorCAD()` 启动 + 保存 .mot) | ✅ 成功 | 23.9 s |
| MATLAB Engine(启动 + version + Simulink 许可证 + sim 探针) | ✅ 成功(Simulink 许可有效、微型模型 sim 通过) | 11.4 s |
| AEDT(pyaedt `Maxwell2d` 无界面 gRPC 启动 + 建设计 + 保存 + 关闭) | ✅ 成功(需用**纯工程名**,见 §4 P4) | 12.2 s |

> readme 声称的 M0 三项验证在本机**可完整复现**。

**补充(2026-08-04 `scripts/check_env.py` 落地时复核)**:MEX C 编译器**实际不可用**——`mex.getCompilerConfigurations('C','Installed')` 返回 **0 个**、`mex('-setup','-n')` 报"未检测到支持的编译器"。本机仅有 VS 18 Community(2026,MSVC 14.51),**不在 MATLAB R2024b 支持列表内**(R2024b 支持至 VS 2022)。readme §3.3/M0"MEX 编译器可用"的声称**不成立**;需安装 VS 2022 Build Tools 或 MATLAB MinGW-w64 支持包(官方推荐,fileexchange 52848)后方可通过 M0 门禁。本报告 §2 E7 行的结论据此修正。

**更新(2026-08-04 当日下午)——MEX 编译器问题已解决**:

- **机制查明**:`mex -v` 详细输出显示 MATLAB R2024b 通过环境变量 **`MW_MINGW64_LOC`** 检测 MinGW64 编译器(查找 `<MW_MINGW64_LOC>\bin\gcc.exe` 并执行 `gcc -dumpversion`),而非本机 PATH 里的裸 gcc;
- **解决方案**:已执行 `setx MW_MINGW64_LOC F:\Env\mingw64`(用户级,无需 admin、无需 MathWorks 账号、零下载),指向本机已有 **gcc 15.2.0**;
- **实测验证**(`scripts/check_env.py` 门禁升级为"实测编译最小 MEX 并调用"):`mex.getCompilerConfigurations('C','Installed')`=1、`mex -setup C` 成功、默认 `mex` 编译 .mexw64 成功并调用返回 42.0;
- **已知残留警告**:gcc 15.2 非 R2024b 官方支持版本(官方为 MinGW 8.1),编译时输出"不受支持的 MinGW 编译器版本"警告,不影响编译与运行;若后续 S-function 编译异常,再升级为官方 MinGW 8.1 支持包(需 MathWorks 账号);
- **M0 门禁最终状态:✅ 全绿(exit 0)**——Motor-CAD 23.2s / MATLAB Engine 14.5s / AEDT gRPC 17.5s。

**更新(2026-08-04 晚)——VS 2022 安装后环境二次标定**:

- **VS 2022 Community 已安装**,MATLAB R2024b 立即识别:`mex.getCompilerConfigurations('C','Installed')` 由 1 变 **2**(MinGW64 Compiler + **Microsoft Visual C++ 2022**);
- **默认编译器已切至 MSVC 2022**(官方支持版本):方法为临时移除用户环境变量 `MW_MINGW64_LOC` → `mex -setup C`(此时仅剩 MSVC 一个候选,非交互直接选定)→ 恢复 `MW_MINGW64_LOC`(MinGW 重新可见但不再默认)。选择持久化于 prefdir `mex_C_win64.xml`(旧 MinGW 配置备份为 `mex_C_win64_backup.xml`);
- **门禁复跑全绿(exit 0)**:Motor-CAD 12.6s / MATLAB Engine 14.6s(默认 MSVC 2022 实测编译 MEX 返回 42.0)/ AEDT gRPC 17.7s;
- **附带验证(M1 模板链)**:`load_from_file()` 可直接加载 .mtt 模板文件并转存 .mot(`templates/motorcad/e7_eMobility_SPM_20kW.mtt` → 551KB .mot 成功);`load_template()` 则按模板库名称加载,不接受任意路径。

---

## 3. 方案可行性评估

- **分层架构**(编排层/各工具控制层/数据层)合理,与 PyAEDT/PyMotorCAD/matlabengine 的能力边界匹配;
- **三种拓扑**(A 全耦合 / B 等效模型 / C 离线)与"批量走 B、关键场景走 A"的策略正确;TB 的 Simulink Co-Simulation 组件(S-function)与 MSML 耦合组件是 Ansys 官方联合仿真路径;
- **匝间短路分段绕组(90%+10%)+ 短路电阻 + 可控开关**是业界标准做法;
- **风险表(§10)覆盖全面**,其中"S-function 编译环境缺失"风险**已在本机实证发生**:MATLAB R2024b 检测不到任何 C 编译器(VS 18 过新),S-function 无法编译,这是 M4 前置阻塞项,建议尽早装 MinGW-w64 支持包或 VS 2022 Build Tools。

---

## 4. 附录 API 速查(§11)逐条核对

基于本机已装包逐方法核对(证据:探测脚本已运行,结论如下):

| 位置 | readme 写法 | 实测 | 正确写法 |
| --- | --- | --- | --- |
| §11.1 | `from ansys.motorcad.core import motorcad; mc = motorcad.MotorCAD()` | **ImportError**(`motorcad` 不是该包导出名) | `from ansys.motorcad.core import MotorCAD; mc = MotorCAD()` |
| §11.1 | `mc.set_variable / do_magnetic_calculation / load_from_file / save_to_file` | 均存在 ✓ | 不变 |
| §11.1 | "导出:几何→Maxwell、dq 磁链图" | `export_to_maxwell` **不存在**;实际为 `export_to_ansys_electronics_desktop(file_path)`(导出 **VBS 脚本**在 AEDT 中运行);`get_maxwell_udm_geometry_json()` 可取 Maxwell UDM 几何 | 用 `export_to_ansys_electronics_desktop`(与 M1"VEDB 脚本导出"说法吻合) |
| §11.1 | dq 磁链图导出 | `export_matrices()` 导出的是 R/L/C 矩阵(**非磁链图**);磁链图需经 `calculate_saturation_map()` / `export_results()` 等确认 | 未定型,与 readme 将 flux map 列入 M1b 待办一致,落地时需先确认 API |
| §11.2 | `Maxwell2d(project="pmsm", solution_type="Transient", design="Motion1", version=..., non_graphical=True)` | 签名一致,**实测可用** ✓ | 不变 |
| §11.2 | `m2d["Br"] = 1.2`(变量赋值) | `__setitem__` 存在 ✓ | 不变 |
| §11.2 | `assign_coil / assign_winding / mesh.assign_length_mesh / analyze / post.create_report` | 均存在 ✓ | 不变 |
| §11.3 | `tb.add_design_variable("R_short", "50mohm")` | **不存在** | `tb["R_short"] = "50mohm"`(或 `tb.variable_manager[...]`) |
| §11.3 | `tb.solve()` | **不存在** | `tb.analyze()` / `tb.analyze_setup(...)` |
| §11.3 | `tb.export_report_csv(...)` | **不存在** | `tb.export_results(...)` |
| §11.3 | TB 电路搭建"通过 AEDT 内部 API/组件模板" | PyAEDT 的 `TwinBuilder` **未封装** Simulink Co-Simulation 组件创建、MSML 导出、故障开关放置 | 需裸 AEDT COM/VBS 脚本(经 `oDesktop`/`odesign` 原始接口),是 M3 最大工作量点 |
| §11.4 | `eng.sim("foc_control", "StopTime", "2.0", nargout=1)` 等 | matlabengine 24.2 接口一致 ✓ | 不变 |

**用法坑(实测发现)**:`Maxwell2d(project=...)` 传**带路径且无 `.aedt` 扩展名**的工程名会触发 `OpenProject` 失败(本机实测 GrpcApiError);应传纯工程名或带扩展名的完整路径。readme §11.2 的纯工程名写法是安全的。

---

## 5. 仓库现状 vs readme 声明

| readme 声明 | 仓库现状 | 结论 |
| --- | --- | --- |
| §3.3/M0: "`scripts/check_env.py` 已实现并全部通过(2026-08-02)" | `scripts/` 目录不存在;全盘搜索(F:\project、F:\simulink、桌面、文档)无 `check_env.py` | ❌ **无代码物证**——readme 声称的 M0 产物未沉淀到本仓库 |
| M1: "模板→参数化→EMag→CSV→AEDT 脚本导出全链路验证" | `models/`、`results/`、`config/` 均不存在,无 .mot/CSV/VBS 产物 | ❌ 同上 |
| §8 代码目录结构 | 仅 `help_md/`(26 个参考文档目录,为 Motor-CAD/AEDT help 导出)+ `readme.md` | ✅ 规划合理,但代码零落盘 |
| M0 ✅ / M1 ✅(2026-08-02) | 本报告 2026-08-04 实机复测**三项启动全部成功** | 环境声明可信,但"已实现"应理解为"已验证可行",而非"代码已存在" |

**推断**:readme 的 M0/M1 ✅ 大概率基于当时的手工/临时脚本验证,验证后未把代码与产物归档到项目仓库。下一步应把 M0 正式落地为 `scripts/check_env.py`(本报告已给出可复现的三项启动调用),并以仓库内物证作为里程碑验收依据。

---

## 6. 需修正的 readme 条目清单

1. **§3.3** conda 环境路径:`C:\Users\win\.conda\envs\pyaedt` → `C:\Env\anaconda3\envs\pyaedt`(与 §3.1 一致);
2. **§3.3/E8** `ANSYS261_DIR` 指向不存在的目录,注明"遗留变量,未使用"或修正值;
3. **§11.1** Motor-CAD 导入名:`motorcad.MotorCAD()` → `MotorCAD()`;导出 API 名改为 `export_to_ansys_electronics_desktop`;
4. **§11.3** TwinBuilder 三个方法名(`add_design_variable`/`solve`/`export_report_csv`)替换为上表正确写法,并注明"TB 电路搭建与 Simulink 联合仿真组件需裸 AEDT COM/VBS 脚本,PyAEDT 无封装";
5. **§11.1 注释** dq 磁链图导出 API 待 M1b 定稿后回填;
6. **里程碑状态** M0/M1 状态栏建议注明"环境验证 ✅(2026-08-04 复测通过),代码落地待办"。

---

## 7. 建议下一步

1. **落地 M0**:新建 `scripts/check_env.py`(快检 imports + full 模式实机启动三项工具),通过后仓库即有 M0 物证;
2. **修正 readme** 上述 6 条,版本组合(含 numpy/pandas 大版本)写入 `config/base.yaml`;
3. **M1**:补 Motor-CAD 模板(`models/motorcad/*.mot` 当前缺失)与 flux map 导出 API 验证;
4. **M2/M3 前置验证**:Motor-CAD→AEDT VBS 导出链路(M1 声称已通,需在仓库内复现)与 TB 电路搭建的 COM 脚本能力摸底,再进入正式实施。
