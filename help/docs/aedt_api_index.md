# PyAEDT API reference 索引（快照 2026-08-17）

来源：https://aedt.docs.pyansys.com/version/stable/API/index.html （stable）

> 已装 pyaedt 1.4.0，导入名 `ansys.aedt.core`（1.x 新命名空间，已实测 `Maxwell2d`/`TwinBuilder` 可导入）。
> 完整方法级文档：在线 API 页面 + 已装包 docstring（`C:\Env\anaconda3\envs\pmsm\Lib\site-packages\pyaedt`）。
> 官方示例：https://github.com/ansys/pyaedt-examples （126MB，未克隆，需要时再拉）。

## App 类（本项目用到的）

| App | 导入名 | 用途 |
| --- | --- | --- |
| Maxwell 2D | `Maxwell2d` | PMSM 电磁 FEM 建模/求解 |
| Maxwell 3D | `Maxwell3d` | 3D 精细化（远期） |
| Twin Builder | `TwinBuilder` | 驱动电路搭建（Simplorer 更名） |
| Circuit | `Circuit` | 通用电路（Maxwell Circuit） |
| RMxprt | `Rmxprt` | 电机设计（备用路线） |

初始化方式（官方推荐）：

```python
from ansys.aedt.core import launch_desktop, Maxwell2d
d = launch_desktop(version="2026.1", non_graphical=False, new_desktop=True, close_on_exit=True)
m2d = Maxwell2d(...)   # 或直接 Maxwell2d(version="2026.1", ...) 隐式启动
d.release_desktop()
```

## 模块分区（本项目相关）

- **Application and solvers**：Desktop / Maxwell2d / Maxwell3d / TwinBuilder / Circuit 等
- **3D/2D modeler**：Modeler / Modeler2D / Primitives（几何建模）
- **Boundary objects**：MaxwellParameters / MaxwellTorque / MaxwellForce 等（力矩/力/矩阵量）
- **Mesh operations**：Mesh / Mesh3d（网格，注意气隙圆柱网格 AnsysAirgapMesh）
- **Setup**：SetupMaxwell（Transient 求解设置）
- **Visualization**：Reports / Post-processing（报告与数据导出）
- **Optimetrics**：ParametricSetups（参数扫描）
- **Variable**：VariableManager / Variable（设计变量）
- **Configuration files**：Configurations（配置模板，可复用工程配置）

## 关键陷阱（前身项目实测，见 AGENTS.md）

- pyaedt gRPC 实例 release 后进程残留并持 .lock → 全 CLI 规避（ansysedt.exe -RunScriptAndExit）
- pyaedt 1.2.0：`Desktop.load_project`（不是 open_project）；gRPC 下 `post.export_report_to_file` 静默不产文件 —— 1.4.0 需回归验证
