# pymotorcad-core API reference 索引（快照 2026-08-17）

来源：https://motorcad.docs.pyansys.com/version/stable/methods/index.html （stable，与已装 0.8.8 对应）

> 提示：完整 RST 文档源码在 `help/repos/pymotorcad/doc/`（克隆自 GitHub main，0.9.dev0），方法级文档以已装包内 docstring 为准（`python -c "from ansys.motorcad.core import MotorCAD; help(MotorCAD.xxx)"`）。

## 顶层 API 分区

- **Motor-CAD API**：`MotorCAD` 类（默认脚本入口），数百个方法，见在线链接
- **Motor-CAD compatibility API**：`MotorCADCompatibility` 类，用于运行旧 ActiveX 脚本（方法文档中注释了对应的新替代函数）
- **Geometry objects and functions**：`ansys.motorcad.core.geometry` —— 0.8.x 新增，Python 定义/修改 Adaptive Templates 几何
- **Geometry tree**：`ansys.motorcad.core.geometry_tree` —— 几何树对象与方法
- **Geometry drawing**：`ansys.motorcad.core.geometry_drawing` —— 几何对象静态可视化（region/line/arc/coordinate 绘制，便于调试 Adaptive Templates 脚本）
- **Geometry shapes**：`ansys.motorcad.core.geometry_shapes` —— 几何计算函数
- **Geometry fitting**：`ansys.motorcad.core.geometry_fitting` —— 用线/弧拟合坐标列表
- **Utility functions**：通用工具
- **Motor-CAD errors**：`MotorCAD_errors` 异常类，处理来自 Motor-CAD 的错误

## 常用方法速查（实测/文档确认）

| 用途 | 方法 |
| --- | --- |
| 打开工程 | `mc.load_from_file(path)`（绝对路径；.mtt/.mot） |
| 加载模板 | `mc.load_template(name)`（按库名，不接受路径） |
| 保存 | `mc.save_to_file(path)` |
| 电磁计算 | `mc.do_magnetic_calculation()` |
| 导出 Maxwell 脚本 | `mc.export_to_ansys_electronics_desktop(path)`（扩展名被强制为 .py） |
| 参数读写 | `mc.set_variable(name, value)` / `mc.get_variable(name)`（须用 activex 名） |
| 数据存储 | `mc.get_datastore()`（dict，key = activex_name） |
| 运行内部脚本 | `mc.run_internal_script(code)` |

## 关键陷阱（前身项目实测，见 AGENTS.md）

- Full Machine 由 `.mot` 条目 `MagneticSymmetry=1` 决定，`set_variable` 改不了（GUI 内部状态）
- 参数化必须用 datastore 的 activex 名，界面名无效
