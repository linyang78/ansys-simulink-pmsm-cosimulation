# 增益计算与整定

> **MathWorks 官方文档存档（中文）**
> 来源：`https://ww2.mathworks.cn/help/mcb/gain-calculation-and-tuning.html`
> 存档：2026-10-21 · R2026b · 英文版：`en/14-gain-calculation-and-tuning.md`
> 说明：本页是分类索引页，下方为官方条目。

---

## 概述

Motor Control Blockset 帮助你为电流环、转速环、位置环选择与调节控制器增益（PI 增益）。
增益最初由电机的电气参数（电阻、电感、惯量）以及各控制环期望的带宽或响应时间算出。

**在 FOC 中先整定电流环（d 轴和 q 轴）**，因为电流环必须快且阻尼良好，才能保证转矩与磁链控制正确。
然后整定转速环，使其比电流环慢，从而保证级联控制稳定。

正确的增益计算与整定对避免振荡、过大转矩脉动、响应迟缓甚至系统不稳定至关重要。

---

## 函数

| 函数 | 用途 |
|---|---|
| `mcb.getPIControllerParameters` | 计算 FOC 中 PI 控制器的增益 |
| `mcb.calcFOCGains` | 计算 PMSM 的 FOC PI 控制器增益与传递函数（R2025a 起） |

---

## 模块

### Controls / Controllers

| 模块 | 说明 |
|---|---|
| **PI Controller** | 通用离散 PI 控制器 |
| **Discrete-time PID Controller** | 离散 PID（R2022a 起） |
| **Field Oriented Control Autotuner** | 在 FOC 应用中自动、顺序整定多个 PID 控制环 |
| **FOC Default Controller Gains** | 按经验法或最优理论在运行期计算 FOC 控制器增益（R2023b 起） |

### 无传感器估计器

| 模块 | 说明 |
|---|---|
| **Sliding Mode Observer** | 估算表贴式 PMSM 的电气位置与机械转速 |
| **Flux Observer** | 估算电气位置、磁链与转子电磁转矩 |
| **Pulsating High Freq Observer** | 用脉振高频（PHF）注入估算 IPMSM 初始电位置（R2022b 起） |
| **Extended EMF Observer** | 估算 PMSM 电气位置与机械转速（R2023a 起） |

### 信号管理

| 模块 | 说明 |
|---|---|
| **PLL with Feed Forward** | 由正交正弦信号计算位置与角频率（R2023b 起） |
| **Compute Parameter** | 通过增加额外输入扩展模块功能（R2024a 起） |

---

## 主题

- **估计控制增益并调节控制参数** —— 为转速与转矩控制子系统执行控制参数整定。
- **为运行电机获取控制器增益（FOC）** —— 演示用最优理论为 FOC 的电流环与转速环求 PI 增益。

---

## 精选示例

| 示例 | 说明 |
|---|---|
| **Tune PI Controllers Using Field Oriented Control Autotuner** | 用 FOC Autotuner 模块计算转速环与电流环 PI 增益 |
| **Tune PI Controllers (in Field-Weakening Control Mode) Using FOC Autotuner Block** | 用 FOC Autotuner 计算**弱磁控制**算法中转速环、电流环、**磁链环**的 PI 增益 |
| **Tune PI Controllers Using Field Oriented Control Autotuner Block on Real-Time Systems** | 在实时系统上整定 |

---

## 对 e11 的落地建议

> 以下为项目批注，非官方原文。

| 环节 | 做法 |
|---|---|
| 电流环增益 | 用 `mcb.getPIControllerParameters`，输入 e11 的 Rs、Ld、Lq 与期望带宽 |
| 转速环增益 | 惯量 J 需要实测或估算（`.mot` 里有转动惯量设定） |
| 整定顺序 | 先 d/q 电流环，再转速环 |
| 弱磁段 | 额外整定磁链环（对应设计 §3.2 电压环） |

第二个精选示例与 e11 直接相关：弱磁模式下多了一个**磁链控制环**（flux control loop），
这是普通 FOC 没有的。设计文档 §3.2 的「电压环兜底」在 MathWorks 的框架里就对应这个磁链环。
