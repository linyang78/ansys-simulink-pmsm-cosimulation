# 设计磁场定向控制算法

> **MathWorks 官方文档存档（中文）**
> 来源：`https://ww2.mathworks.cn/help/mcb/ug/design-field-oriented-control-algorithm.html`
> 存档：2026-10-21 · R2026b · 英文版：`en/07-design-field-oriented-control-algorithm.md`
> 说明：这是「设计 FOC 算法」五步工作流的**总纲页**（R2026b；早期版本分 4 步，新增了
> 电流/位置换算一步）。各步骤的详细页面按需单独存档。

---

## 总纲

要为电机实现转速控制算法，请执行以下任务：

- **电流换算**：将电流从 ADC 计数转换为 PU
- **正交编码器位置解码**：读取正交编码器位置计数并计算转子电气位置
- **转矩控制**：在 *d*-*q* 轴中实现电流控制
- **转速控制**：实现转速控制

这些步骤帮助使用 Motor Control Blockset™ 为 PMSM 实现转速控制算法，
与示例《使用正交编码器的 PMSM 磁场定向控制》中使用的模型 `mcb_pmsm_foc_qep_f28379d` 相关。
它们解释调节 *d* 轴与 *q* 轴电流控制器以及转速控制器控制参数的过程。

---

## 五步工作流

| 步 | 页面 | 内容 |
|---|---|---|
| 1 | Design Current and Position Scaling Subsystems | 电流/位置标幺换算子系统（ADC 计数 → PU） |
| 2 | Design Current Controller Subsystem | 电流控制器子系统（PI + Clarke/Park + PWM 生成） |
| 3 | Perform Manual Gain-Tuning of Current Controller | 电流控制器手动增益整定 |
| 4 | Design Speed Control Algorithm | 转速控制算法（外环） |
| 5 | Perform Manual Gain-Tuning of Speed Controller | 转速控制器手动增益整定 |

这些步骤用变量定义电流控制器与转速控制器的数据类型与执行时间。
关于这些变量的细节，参阅与示例模型 `mcb_pmsm_foc_qep_f28379d` 关联的初始化脚本。

> **提示**：遵循此工作流的前提是了解 Simulink® 基础知识，
> 因为这些步骤不提供「在 Constant 模块中定义数据类型」或「使用数学运算模块」等任务的细节。

关于估计电机参数，请参阅《使用参数估计模块估计 PMSM 参数》；
关于设计被控对象模型，请参阅《使用 Motor Control Blockset 创建被控对象模型》。
这有助于在仿真中验证控制算法。

---

## 与本存档其他文档的关系

```
① 13-estimate-pmsm-parameters         拿电机参数（Rs/Ld/Lq/Ke/J/B）
② 05-creating-plant-model             搭被控对象（电机 + 逆变器 + 采样 + 延迟）
③ 本页                               搭控制器（换算 → 电流环 → 转速环）
④ 08-design-current-controller        第 2 步的详细展开
⑤ 15-estimate-control-gains-and-tune  算 PI 增益
⑥ 09-field-oriented-current-controller 成品电流控制模块参考
```

---

## 另请参阅

- Design Current Controller Subsystem
- Design Speed Control Algorithm
- Field-Oriented Control of PMSM Using Quadrature Encoder

---

## 对 e11 的含义

> 以下为项目批注，非官方原文。

💡 e11 项目不需要从零搭这五步——直接用 MCB 成品模块
（Field-Oriented Current Controller + LUT based PMSM Control Reference）更快。

但这五步是**理解成品模块内部在做什么**的最好材料，
特别是在联合仿真里要判断「模块行为 vs ECE 行为」谁对谁错时。

建议至少精读**第 1 步（换算）**和**第 2 步**（存档见 `08-design-current-controller.md`）。
