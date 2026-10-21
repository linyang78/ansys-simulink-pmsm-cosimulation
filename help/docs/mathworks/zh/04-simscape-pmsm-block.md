# PMSM（Simscape Electrical 模块）

> **MathWorks 官方文档存档（中文）**
> 来源：`https://ww2.mathworks.cn/help/simscape-electrical/ref/pmsm.html`（正文取自英文站）
> 存档：2026-10-21 · R2026b · 英文版：`en/04-simscape-pmsm-block.md`
> 说明：这是 Simscape Electrical 的电机本体模块，与 Motor Control Blockset 的控制算法模块不同。
> 它可用来搭建被控对象（plant），作为「把 ECE 模型放在 Twin Builder」的替代路线。

---

## 描述

PMSM 模块用于建模三相 Y 接、Δ 接或开口绕组的永磁同步电机。
可建模内置式（IPMSM）、表贴式（SPMSM）、横向磁通电机、轴向磁通（盘式）电机或 PMSM 伺服电机。

PMSM 有永磁转子与绕线定子，用于电动车等牵引场景与作动系统。
在作动系统里也叫无刷伺服电机。
PMSM 通常具有**正弦反电动势**，相比反电动势为梯形的无刷直流（BLDC）电机，
可减小不期望的高频机械与电流谐波。

模块以恒定的 d 轴、q 轴电感 Ld、Lq 建模。两种主类型：

- **SPMSM**：磁钢表贴，**Ld = Lq**
- **IPMSM**：磁钢内置，**Ld ≠ Lq**

也可按主磁通路径分类：常见为径向，轴向磁通在同样体积下能给出高得多的转矩。

用 **Winding type** 参数指定绕组形式（Y 接 / Δ 接 / 开口）。

> [图：Y 接定子的等效电路]

Simscape™ Electrical™ 里有多个模块能建模同类电机。
应选「建模细节足以回答你的工程问题」的那个；不要用细节过度的模块——保真度越高，仿真越慢、参数化越复杂。

PMSM 模块用简单等效电路 + 固定或参数化系数来建模，属中等保真度。
适用于作动应用（机器人、机电）的控制/系统设计，以及饱和与谐波对损耗影响较弱时的效率预测。

---

## 电机构造

> [图：转子上单对极的电机构造]

永磁体产生转子磁场，随转子角度形成正弦变化的磁通。

关于轴向约定：把 **Rotor angle definition** 设为 *a 相磁轴与 d 轴夹角* 时，
转子机械角 θr 为 0 时 a 相磁链与永磁磁链对齐；
设为 *a 相磁轴与 q 轴夹角* 时，转子机械角是 a 相磁轴与转子 q 轴的夹角。

---

## 方程

定子绕组电压：

```
[va]   [Rs  0   0 ] [ia]   [dψa/dt]
[vb] = [0   Rs  0 ] [ib] + [dψb/dt]
[vc]   [0   0   Rs] [ic]   [dψc/dt]
```

永磁体与三相绕组共同贡献每相总磁链：

```
[ψa]   [Laa Lab Lac] [ia]   [ψam]
[ψb] = [Lba Lbb Lbc] [ib] + [ψbm]
[ψc]   [Lca Lcb Lcc] [ic]   [ψcm]
```

电感随转子电角度变化：

```
θe = N·θr + rotor offset

Laa = Ls + Lm·cos(2θe)
Lbb = Ls + Lm·cos(2(θe − 2π/3))
Lcc = Ls + Lm·cos(2(θe + 2π/3))

Lab = Lba = −Ms − Lm·cos(2(θe + π/6))
Lbc = Lcb = −Ms − Lm·cos(2(θe + π/6 − 2π/3))
Lca = Lac = −Ms − Lm·cos(2(θe + π/6 + 2π/3))
```

- `θr`：转子机械角；`θe`：转子电角度
- `rotor offset`：以 d 轴定义时为 0，以 q 轴定义时为 −π/2
- `Ls`：每相自感平均值
- `Lm`：电感波动量
- `Ms`：相间互感平均值

a 相永磁磁链在 θe = 0° 时最大、θe = 90° 时为零：

```
[ψam]   [ψm·cos(θe)        ]
[ψbm] = [ψm·cos(θe − 2π/3) ]
[ψcm]   [ψm·cos(θe + 2π/3) ]
```

---

## Park 变换后的简化方程

对电气方程施加 Park 变换，可得到与转子角度无关的转矩表达式。Park 变换定义为：

```
P = (2/3) × [ cos θe        cos(θe−2π/3)        cos(θe+2π/3)  ]
            [ −sin θe       −sin(θe−2π/3)       −sin(θe+2π/3) ]
            [ 0.5           0.5                 0.5           ]
```

其中 θe = N·θr，N 为极对数。

变换后得到模块的行为方程：

```
vd = Rs·id + Ld·did/dt − N·ω·iq·Lq
vq = Rs·iq + Lq·diq/dt + N·ω·(id·Ld + ψm)
v0 = Rs·i0 + L0·di0/dt

T = (3/2)·N·( iq·(id·Ld + ψm) − id·iq·Lq )
```

其中：

- `Ld = Ls + Ms + (3/2)·Lm` —— d 轴定子电感
- `Lq = Ls + Ms − (3/2)·Lm` —— q 轴定子电感
- `L0 = Ls − 2·Ms` —— 零序电感
- `ω`：转子机械角速度；`N`：极对数
- `T`：转子转矩（从机壳端口 C 流向转子端口 R）

⚠️ 本模块用的是 **Park 变换的原始非正交形式**。换成另一种（等功率）形式，dq0 电压电流结果会不同。

> 对联合仿真的含义：Twin Builder 的 ECE 组件内部也有自己的一套 Park 变换实现。
> 两边不一致时 dq 电流会出现偏差，**联调前要先核对 Park 变换的系数约定**。

---

## 替代参数化：反电势常数与转矩常数

可用数据手册上更常见的反电势常数或转矩常数来参数化电机：

```
ke = N·ψm      （反电势常数，V·s/rad）
eph = ke·ω     （单相反电势）
kt = N·ψm      （转矩常数，N·m/A）
```

在 SI 单位下，转矩常数与反电势常数的**数值相同**。

当 Ld = Lq 且三相对称时：

```
T = (3/2)·kt·iq = (3/2)·kt·Ipk
kt = (2/3)·(T / Ipk)
kt = (2/3)·(T / iline,rms)
```

---

## 铁损计算

铁损分两项：主磁化路径，以及**弱磁运行时才激活的齿顶跨路径**。

### 主磁化路径

```
POC(Vmrms) = ah·k·Vmrms + aj·k²·Vmrms² + aex·k^1.5·Vmrms^1.5
```

空载时该项主导。`k = Vmrms/f`（每 Hz 有效值电压，即反电势常数）。
三项分别是磁滞损耗、涡流损耗、附加损耗。

### 齿顶跨路径（弱磁时重要）

```
PSC(Vdrms*) = bh·k·Vdrms* + bj·k²·Vdrms*² + bex·k^1.5·Vdrms*^1.5
```

由 FEA 短路试验确定。

---

## 预定义参数化

模块提供多套内置参数化，可按供应商的具体型号配置。
双击模块 → 点 **Selected part** 的 `<click to select>` → 在 Block Parameterization Manager 中选型。

注意：预定义参数化用可得数据源填值，缺失处靠工程判断与简化假设补齐，
因此仿真与真实行为会有偏差，需用实测数据校验。

---

## 热效应建模

**Modeling option** 可选：

- **No thermal port**：只有定子绕组的电气端口，无热端口
- **Show thermal port**：除电气端口外，还有各绕组与转子的热端口

---

## 生成派生数据表（R2026a 起）

可生成类似器件厂商数据手册的汇总表与特性曲线，包含：

- 峰值转矩与最大交流电压下的转矩、电流随转速变化
- 50% 与 100% 额定定子电流下的转矩、效率、轴功率、定子电流随转速变化

操作：模块对话框 **Utilities** 区的 **Derived data sheet** 旁点 **Open live script**，
填入峰值线电流、最大允许线电流、最大定子线电压峰值、额定转速、最高转速，点 **Generate Data Sheet**。

---

## 关键参数

| 参数 | 默认 | 说明 |
|---|---|---|
| **Modeling option** | No thermal port | 是否启用热端口 |
| **Electrical connection** | Composite three-phase ports | 复合端口 / 展开端口 |
| **Winding type** | Wye-wound | Y 接 / Δ 接 / 开口 |
| **Modeling fidelity** | Constant Ld, Lq and PM | 恒定 / **Tabulated（查表）** |
| **Number of pole pairs** | 6 | 极对数 |
| **Permanent magnet flux linkage** | 0.03 Wb | 永磁磁链 |
| **Stator d-axis inductance, Ld** | 0.00022 H | d 轴电感 |
| **Stator q-axis inductance, Lq** | 0.00022 H | q 轴电感 |
| **Direct-axis current vector, iD** | [-200, 0, 200] A | 查表模式的 d 轴电流向量 |
| **Quadrature-axis current vector, iQ** | [-200, 0, 200] A | 查表模式的 q 轴电流向量 |
| **Ld matrix, Ld(id,iq)** | 0.0002·ones(3,3) H | 查表模式 |
| **Lq matrix, Lq(id,iq)** | 0.0002·ones(3,3) H | 查表模式 |
| **Permanent magnet flux linkage, PM(id,iq)** | 0.1·ones(3,3) Wb | 查表模式 |
| **Stator resistance per phase, Rs** | 0.013 Ohm | 每相电阻 |
| **Rotor angle definition** | a 相磁轴与 d 轴夹角 | 必须与 ECE 的约定一致 |
| **Rotor inertia** | 0.01 kg·m² | 转动惯量 |
| **Rotor damping** | 0 N·m/(rad/s) | 阻尼 |

---

## 示例

- Electric Power Assisted Steering —— 电动助力转向
- **Model Faulted PMSM** —— 故障 PMSM（绕组故障需在磁域层面建模）
- Model a Three-Phase PMSM Drive —— 三相 PMSM 驱动完整系统
- Three-Phase PMSM Drive with Thermal Model —— 带热模型与铁损
- Parameterize a Permanent Magnet Synchronous Motor —— 由反电势/转矩常数反推磁链
- **IPMSM Torque Control** —— IPMSM 转矩控制（开环转矩 + 闭环电流）
- **IPMSM Velocity Control** —— IPMSM 转速控制（外环转速 + 双内环电流，Stateflow 调度）
- IPMSM Torque-Based Load Control —— 转矩型负载控制
- Control Velocity of Three-Phase PMSM with Open-End Winding —— 开口绕组三相 PMSM 调速（R2025a 起）
- IPMSM Outer Loop Controller Evaluation —— 外环控制器评估

---

## 另请参阅

**Simscape 模块：** BLDC | FEM-Parameterized PMSM | FEM-Parameterized Synchronous Machine |
Hybrid Excitation PMSM | Magnetic Rotor | Motor & Drive (System Level) | PMSM (DQ0) | Rotating Air Gap

**主题：** Simscape Electrical Part Collection | Choose Blocks to Model Motors or Actuators |
Expand and Collapse Three-Phase Ports on a Block

## 参考文献

[1] Kundur, P. *Power System Stability and Control*. New York, NY: McGraw Hill, 1993.

[2] Anderson, P. M. *Analysis of Faulted Power Systems*. Hoboken, NJ: Wiley-IEEE Press, 1995.

[3] Mellor, P.H., R. Wrobel, and D. Holliday. "A computationally efficient iron loss model for brushless AC
machines that caters for rated flux and field weakened operation." IEEE Electric Machines and Drives
Conference. May 2009.

---

## 对 e11 的落地建议

> 以下为项目批注，非官方原文。

⭐ **模块的 `Modeling fidelity = Tabulated Ld, Lq and PM` 模式是重点。**
把 `results/e11-ece-91x91/` 的 (id, iq) 网格数据填进 `Ld matrix`、`Lq matrix`、
`Permanent magnet flux linkage matrix`，就能在 Simulink 里复现 e11 的饱和特性。

e11 取值：

| 参数 | e11 值 |
|---|---|
| `Number of pole pairs` | **4** |
| `Permanent magnet flux linkage` | **0.075883 Wb** |
| `Stator d-axis inductance, Ld` | **2.26e-4 H**（饱和后 1.61e-4） |
| `Stator q-axis inductance, Lq` | **2.97e-4 H**（轻载 6.65e-4） |
| `Stator resistance per phase, Rs` | **0.01338 Ohm**（65 ℃） |

⚠️ `Rotor angle definition` 必须与 ECE 组件的 `IniPos` 约定一致，否则 dq 电流会差 90°。

💡 `IPMSM Velocity Control` 示例与本项目控制结构几乎一致（外环转速 + 双内环电流、多速率 PI 级联、
Stateflow 任务调度），可作为 `.slx` 控制模型的参照模板。
