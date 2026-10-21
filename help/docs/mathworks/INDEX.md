# MathWorks 文档目录 · 编号与学习顺序

> 目录：`en/`（英文）、`zh/`（中文）——**同一编号在两个文件夹里是同一篇文档**
> 存档版本：R2026b · 整理日期：2026-10-21 · 共 17 篇，全部完成拆分

## 一、完整清单（按学习顺序编号）

| 编号 | 主题 | 学习阶段 | ★ |
|---|---|---|---|
| **01** | Field-Oriented Control（FOC 原理） | 阶段 0 全景 | |
| **02** | Open-Loop and Closed-Loop Control（开环/闭环） | 阶段 0–2 | |
| **03** | PMSM Drive Characteristics and Constraint Curves（约束曲线） | 阶段 1 数学模型 | ★ |
| **04** | PMSM Block（Simscape 电机本体） | 阶段 1 建模 | |
| **05** | Creating Plant Model（创建被控对象） | 阶段 1 建模 | |
| **06** | Per-Unit System（标幺制） | 阶段 2 标幺 | |
| **07** | Design FOC Algorithm（设计 FOC 总纲） | 阶段 3 控制环 | |
| **08** | Design Current Controller（电流控制器子系统） | 阶段 3 控制环 | |
| **09** | Field-Oriented Current Controller（成品模块） | 阶段 3 控制环 | |
| **10** | FOC of PMSM Using Quadrature Encoder（标杆示例） | 阶段 3 控制环 | |
| **11** | MTPA Control Reference（MTPA 模块） | 阶段 4 MTPA | ★ |
| **12** | Field-Weakening Control with MTPA（弱磁示例） | 阶段 4 弱磁 | |
| **13** | Estimate PMSM Parameters（参数估计） | 阶段 5 参数 | |
| **14** | Gain Calculation and Tuning（增益索引页） | 阶段 5 整定 | |
| **15** | Estimate Control Gains and Tune（增益整定详解） | 阶段 5 整定 | |
| **16** | FW Control of Nonlinear PMSM Using LUT（查表弱磁） | 阶段 6 LUT 实战 | ★★ |
| **17** | LUT based PMSM Control Reference（LUT 模块） | 阶段 6 LUT 实战 | ★★ |

★ = 学习重点；★★ = 最贴合 e11 项目

## 二、建议阅读顺序

```
阶段 0 全景       01 → 02
阶段 1 电机本体   03 → 04 → 05
阶段 2 变换与标幺  06（配合 01、02 复习）
阶段 3 FOC 控制环  07 → 08 → 09 → 10
阶段 4 MTPA/弱磁   11 → 12
阶段 5 参数与整定  13 → 15（14 是索引页，可略读）
阶段 6 LUT 实战    16 → 17          ← 本项目核心
```

完整学习计划（含先修检查、动手实验、验收标准、自测题）见 `../pmsm-learning-roadmap.md`。
知识点整理版见 `../ipm-foc-mtpa-field-weakening.md`。

## 三、目录结构

```
help/docs/mathworks/
├── INDEX.md      ← 本文件
├── README.md     ← 源地址与访问说明
├── en/           ← 英文版（17 篇）
│   ├── 01-field-oriented-control.md
│   ├── 02-open-loop-and-closed-loop-control.md
│   ├── 03-pmsm-characteristics-constraint-curves.md
│   ├── 04-simscape-pmsm-block.md
│   ├── 05-creating-plant-model.md
│   ├── 06-per-unit-system.md
│   ├── 07-design-field-oriented-control-algorithm.md
│   ├── 08-design-current-controller.md
│   ├── 09-field-oriented-current-controller.md
│   ├── 10-foc-pmsm-using-quadrature-encoder.md
│   ├── 11-mtpa-control-reference.md
│   ├── 12-field-weakening-control-mtpa-pmsm.md
│   ├── 13-estimate-pmsm-parameters.md
│   ├── 14-gain-calculation-and-tuning.md
│   ├── 15-estimate-control-gains-and-tune.md
│   ├── 16-fwc-mtpa-nonlinear-pmsm-lut.md
│   └── 17-lut-based-pmsm-control-reference.md
└── zh/           ← 中文版（17 篇，文件名与 en/ 完全相同）
```

## 四、拆分原则

- **逐段搬运，不重写、不概括**；代码块与表格在两版中完整保留
- **项目批注（⚠️ / 💡）只放在中文版**，英文版保持纯官方原文
  ——这样英文版可以当作「官方标准答案」，用于核对中文理解与项目judgment
- 官方无中文翻译的页面（08、09、17 等），中文版明确标注「整理者翻译」
- 原文页面的图片（FOC 架构图、子系统框图等）以 `> [Figure: ...]` 占位标注

## 五、对 e11 的关键取值（散落在各篇，汇总于此）

| 量 | 值 | 出处 |
|---|---|---|
| 极对数 p | 4 | 设计文档 §2.1（`.mot:6571`） |
| 永磁磁链 λpm | 0.075883 Wb | `03` / `04` 的 e11 批注 |
| Ld | 226 µH（Id=−433 A）/ 242 µH（近零） | `03` / `04` |
| Lq | 297 µH（满载）/ 665 µH（轻载） | `03` / `04` |
| Rs（65 ℃） | 13.38 mΩ | `03` / `04` |
| 标幺基压 V_base（SVM） | **230.94 V** = 400/√3 | `06` |
| 满载基速 | 约 4,040 rpm | `03` / `06` |
| MTPA 最优点 | Id=−303.1、Iq=303.1 → 246.4 N·m | 设计文档 §3.1.1 |
