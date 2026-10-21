# IPM 电机原理与 FOC / MTPA / 弱磁控制 —— 学习笔记

> 资料源：MathWorks Motor Control Blockset 官方文档（下文标注链接）+ 本机随附示例
> `help/matlab-examples/field-weakening-mtpa/`（R2024b，18 个文件）
> 结合本项目 e11 电机的 ECE 实测数据（`results/e11-ece-61x61/`）
> 整理日期：2026-10-21

## 0. 一句话

IPM 的转子把磁钢埋在铁芯里，d 轴磁路被磁钢"堵住"（磁钢磁导率≈空气），所以 **Ld < Lq**；
这个凸极差产生磁阻转矩，于是同一个电流能出更大转矩（MTPA）；转速升高后反电势顶到母线电压，
需要往 d 轴灌**负电流**去削弱磁链（弱磁），才能继续升速。

## 1. IPM 与 SPMSM 的本质区别

| 项 | SPMSM（表贴式） | IPM（内置式） |
|---|---|---|
| 磁钢位置 | 转子表面 | 埋在转子铁芯内 |
| 电感关系 | Ld ≈ Lq（无凸极） | **Ld < Lq**（凸极） |
| 转矩成分 | 只有永磁转矩 | 永磁转矩 + **磁阻转矩** |
| 最优电流 | id = 0 | **id < 0**（用负 id 换磁阻转矩） |
| 弱磁方法 | CVCP（恒压恒功率） | **VCLMT**（电压电流受限最大转矩） |

**关键认知**：`Ld < Lq` 是 IPM 的**正常**特征，不是异常。
MathWorks 的 MTPA 公式直接以 `Lq > Ld` 为前提书写（见 §5）。
本项目 e11 实测 Ld≈0.23 mH、Lq≈0.30 mH（额定电流处），符合该前提。

## 2. PMSM 在 dq 轴上的数学模型

MathWorks《MTPA Control Reference》给出的模型方程：

```
vd = id·Rs + dλd/dt − ωe·Lq·iq
vq = iq·Rs + dλq/dt + ωe·Ld·id + ωe·λpm

λd = Ld·id + λpm
λq = Lq·iq

Te = (3/2)·p·[ λpm·iq + (Ld − Lq)·id·iq ]
Te − TL = J·dωm/dt + B·ωm
```

| 符号 | 含义 | 单位 |
|---|---|---|
| `vd` / `vq` | d/q 轴电压 | V |
| `id` / `iq` | d/q 轴电流 | A |
| `Rs` | 定子每相电阻 | Ω |
| `λpm` | 永磁磁链 | Wb |
| `λd` / `λq` | d/q 轴磁链 | Wb |
| `Ld` / `Lq` | d/q 轴电感 | H |
| `ωe` / `ωm` | 电角速度 / 机械角速度 | rad/s |
| `p` | 极对数 | — |
| `Te` / `TL` | 电磁转矩 / 负载转矩 | N·m |
| `J` / `B` | 转动惯量 / 摩擦系数 | kg·m² / kg·m²·s⁻¹ |

**转矩公式的第二项就是磁阻转矩**：`(Ld − Lq)·id·iq`。
因 `Ld < Lq`，该项在 `id < 0`、`iq > 0` 时为正 —— 这就是"负 id 增转矩"的来源。

## 3. 两条约束：电流圆与电压椭圆

控制器的可行域由两条约束的交集决定。

**电流约束（圆）**，由逆变器/电机热限决定：

```
imax² = id² + iq²
```

**电压约束（椭圆）**，由母线电压决定（忽略电阻时）：

```
vd0 = −ωe·Lq·iq
vq0 = ωe·(Ld·id + λpm)
vd0² + vq0² ≤ vmax²
  ⇒  (Lq·iq)² + (Ld·id + λpm)² ≤ (vmax/ωe)²
```

`vmax` 取变频器能输出的最大基波相电压峰值。对 SVPWM 线性调制区：`vmax = Vdc/√3`。
考虑电阻压降时 MathWorks 写作 `vmax = Vdc/√3 − Rs·imax`。

**物理含义**：转速 ωe 越高，允许的磁链模值 `vmax/ωe` 越小 —— 椭圆不断收缩。
当椭圆缩到装不下当前电流点时，就必须减小 d 轴磁链（灌负 id），即弱磁。

第三条约束是**温度**，不属于电磁可行域，但同样限制可持续转矩；高速运行时必须监测。

## 4. 基速（base speed）

定义：在额定电压、额定负载下，不进入弱磁区时能达到的最高转速。

```
ωbase = (1/p) · vmax / sqrt( (Lq·iq)² + (Ld·id + λpm)² )
```

- 低于基速：恒转矩区（电流受限），可做 MTPA；
- 高于基速：恒功率区（电压受限），转矩随转速反比下降。

**e11 实算**（λpm=0.075883 Wb，Vdc=400 V，p=4，Imax=433 A）：

| 工况 | 磁链模值 | 基速 |
|---|---|---|
| 满载（Iq≈433 A，d 轴取最优） | 约 0.137 Wb | **约 4,040 rpm** |
| 轻载 | 更低 | 更高（反电势尚未顶到母线） |

> 注意：负载越轻，基速越高。讨论"基速"必须带工况，否则没有意义。

## 5. MTPA：每安培最大转矩

**目标**：在 `im = sqrt(id² + iq²)` 固定的前提下，找使 `Te` 最大的 (id, iq)。

**IPM 的解析解**（MathWorks 给出，假设 Ld/Lq 为常数）：

```
im_ref = 2·Tref / (3·p·λpm)
im     = min(im_ref, imax)

id_mtpa = λpm / (4·(Lq − Ld)) − sqrt( λpm² / (16·(Lq − Ld)²) + im²/2 )
iq_mtpa = sqrt( im² − id_mtpa² )
```

**SPMSM**：因 Ld = Lq，磁阻项消失，MTPA 退化为 `id = 0`、`iq = Tref / (1.5·p·λpm)`。

**饱和怎么办**：上式假设电感恒定。实际 Ld/Lq 随电流显著变化
（e11 实测：Ld 从 242 µH 降到 161 µH，Lq 从 665 µH 降到 297 µH）。
两种可用做法：

1. **解析式 + 恒值电感**：快，误差来自饱和；
2. **查表**：在 ECE/FEA 数据上直接搜最优点，精度最高。MathWorks 也提供
   "Vector Control Reference 块手工扫转矩角"的做法来为非线性电机建 MTPA 表。

## 6. 弱磁：越过基速之后

### 6.1 原理

反电势 `E = ωe·λpm` 随转速上升，超过 `vmax` 后电流环无法再维持电流。
此时给 d 轴灌负电流，使 `λd = Ld·id + λpm` 减小，等效削弱转子磁链，从而降低反电势。

代价：同一电流圆下可用于 `iq` 的份额减少，转矩下降 → 进入恒功率区。

### 6.2 SPMSM 用 CVCP（恒压恒功率）

```
若 ωm ≤ ωbase:
    id_mtpa = 0
    iq_mtpa = Tref / (1.5·p·λpm)
    id_sat = 0
    iq_sat = sat(iq_mtpa, imax)
否则:
    id_fw  = (ωe_base − ωe)·λpm / (ωe·Ld)
    id_sat = max(id_fw, −imax)
    iq_fw  = Tref / (1.5·p·λpm)
    iq_lim = sqrt(imax² − id_sat²)
    iq_sat = sat(iq_fw, iq_lim)
```

### 6.3 IPMSM 用 VCLMT（电压电流受限最大转矩）

先求"给定转速下的最大转矩电流"（电压椭圆与电流圆的交点）：

```
(Ld² − Lq²)·id² + 2·λpm·Ld·id + λpm² + Lq²·imax² − vmax²/ωe² = 0

id_fw = −λpm/Ld
      + sqrt( (λpm/Ld)² − (Ld² − Lq²)·(λpm² + Lq²·imax² − vmax²/ωe²) / (Ld² − Lq²) )
iq_fw = sqrt(imax² − id_fw²)
```

再求"给定转速与给定转矩下的电流"，需解关于 `iq_fw` 的四次方程（MathWorks 文档给出完整式，
并在"Prioritise execution time"打开时用近似代替迭代求解）。

**两段的切换**：

```
若 ωm ≤ ωbase:  Idref = id_mtpa,  Iqref = iq_mtpa
否则:           Idref = max(id_fw, −imax)
                iq_fw = sqrt(imax² − id_fw²)
                Iqref = min(iq_fw, im)
```

## 7. MTPA Control Reference 模块参数怎么配

| 参数 | 含义 | e11 取值 |
|---|---|---|
| `Type of motor` | Interior / Surface PMSM | **Interior PMSM** |
| `Number of pole pairs` | 极对数 | **4**（8 极） |
| `Stator resistance per phase (Ohm)` | 每相电阻 | **0.01338**（65 ℃） |
| `Stator d-axis inductance (H)` | Ld | **2.3e-4**（饱和后 1.6e-4） |
| `Stator q-axis inductance (H)` | Lq | **3.0e-4**（饱和后 3.0e-4，轻载 6.6e-4） |
| `Permanent magnet flux linkage (Wb)` | λpm | **0.075883** |
| `Max current (A)` | 电流上限（峰值） | **433** |
| `Vdc input method` | 固定 / 输入端口 | 视仿真而定 |
| `DC voltage (V)` | 母线电压 | **400** |
| `Input units` | Per-Unit / SI | 建议 **SI Units**（与 ECE 数据一致） |
| `Base speed (rpm)` | 基速 | 约 **4040**（满载） |
| `Prioritise execution time` | 用近似加速 | 精度优先时**关闭** |

⚠️ 恒值电感与饱和数据的差距：e11 的 Ld 在 161–242 µH、Lq 在 297–665 µH 之间变化。
若追求精度，应改用查表方案（见 §9）；模块参数法只适合先跑通链路。

## 8. 本机示例：Field-Weakening Control (with MTPA) of PMSM

**位置**：`C:\Users\<user>\Documents\MATLAB\Examples\R2024b\mcb\FieldWeakeningControlWithMTPAExample`
（本项目已复制到 `help/matlab-examples/field-weakening-mtpa/`）

### 8.1 文件构成

| 文件 | 用途 |
|---|---|
| `FieldWeakeningControlWithMTPAExample.m` | 主脚本（说明 + 启动模型） |
| `mcb_pmsm_fwc_host_model.slx` | **上位机界面模型**（串口通信、参数下发、示波器） |
| `mcb_pmsm_mtpa_host_model.slx` | MTPA 专用的上位机模型 |
| `mcb_pmsm_fwc_qep_f28379d.slx` | 目标机模型（F28379D + QEP 编码器） |
| `mcb_pmsm_fwc_qep_f28069LaunchPad.slx` | 目标机模型（F28069 LaunchPad） |
| `mcb_ipmsm_fwc_qep_f28379d.slx` | **IPMSM 专用**目标机模型（ADLEE-BM-180E） |
| `mcb_pmsm_mtpa_qep_*.slx` | 只做 MTPA（不含弱磁）的目标机模型 |
| `mcb_*_data.m` | 各硬件的模型初始化脚本（电机/逆变器/传感器参数） |
| `mcb_fwc_charac.png` 等 | 特性曲线示意（恒转矩区/恒功率区、MTPA 曲线） |

### 8.2 示例的三种参考电流生成方式

主脚本明确列出（`FieldWeakeningControlWithMTPAExample.m:177-195`）：

1. **MTPA Control Reference 块** —— 解析计算，假设线性电感；
2. **Vector Control Reference 块手工扫转矩角** —— 为非线性电感（饱和）电机建 MTPA 表；
3. **不用 MTPA** —— 对照组。

脚本给出的对比读数：MTPA 时电转矩 0.34 PU，不用 MTPA 时 0.27 PU（提升约 26%）。

### 8.3 示例里的 IPMSM 说明（对本项目有直接参考价值）

> ADLEE-BM-180E 的凸极率约 10%（Lq 比 Ld 高约 10%），因凸极率低，进入弱磁区需要更大的 id，
> 很快撞到额定电流（9 A），却只能换来有限的升速。

这条经验说明：**凸极率低的 IPM，弱磁的"性价比"差**。
e11 在额定电流处 Lq/Ld ≈ 1.3（凸极率约 30%），比 ADLEE 好，但低于典型高凸极 IPM（2–3 倍）。

### 8.4 运行要求

- 仿真：Motor Control Blockset（F28069 模型另需 Fixed-Point Designer）
- 代码生成：Embedded Coder + C2000 Microcontroller Blockset
- **本项目只需仿真**：`mcb_pmsm_fwc_host_model.slx` 与目标机模型配合才是硬件部署路线；
  纯仿真请用 `mcb_pmsm_fwc_qep_f28379d.slx` 直接 Run

## 9. 落到 e11：建议做法

| 环节 | 做法 | 依据 |
|---|---|---|
| MTPA / 弱磁电流分配 | **查表**（(Te*, ω) → (Id*, Iq*)），不用解析式 | e11 电感随电流变化 50% 以上，解析式误差大 |
| 表的数据来源 | `results/e11-ece-61x61/`（61×61 电流网格 × 41 位置） | 网格密度足够分辨电压椭圆边界 |
| 电压环兜底 | |Vdq| > 0.95·vmax 时把 Id* 往负方向推 | 查表管稳态轨迹，电压环抑制参数误差与瞬态 |
| 分段判据 | 用 `|λ| ≤ vmax/ωe` 判断是否进入弱磁，不用固定转速 | 基速随负载变化（§4） |

## 10. 参考资料

**MathWorks 官方（在线）**

| 主题 | 链接 |
|---|---|
| MTPA Control Reference（全部公式） | https://www.mathworks.com/help/mcb/ref/mtpacontrolreference.html |
| Field-Weakening Control (with MTPA) of PMSM | https://www.mathworks.com/help/mcb/gs/field-weakening-control-mtpa-pmsm.html |

**经典文献（示例脚本给出的参考文献）**

1. B. Bose, *Modern Power Electronics and AC Drives*, Prentice Hall, 2001.
2. Morimoto, Sanada, Takeda, "Wide-speed operation of interior permanent magnet synchronous motors
   with high-performance current regulator," *IEEE Trans. Ind. Appl.*, vol. 30, no. 4, 1994, pp. 920-926.
3. Li, Muyang, "Flux-Weakening Control for PMSMs Based on Z-Source Inverters," Master's Thesis,
   Marquette University, 2014.
4. Briz, Degner, Lorenz, "Analysis and design of current regulators using complex vectors,"
   *IEEE Trans. Ind. Appl.*, vol. 36, no. 3, 2000, pp. 817-825.

**本项目内部资料**

| 内容 | 位置 |
|---|---|
| e11 电机参数与 ECE 结论 | `docs/design/e11-control-model.md` §2、§3.1.1 |
| ECE 高精度扫描数据 | `results/e11-ece-61x61/`（SML/TXT/MAT 三件套） |
| 官方示例（已复制） | `help/matlab-examples/field-weakening-mtpa/` |
| Twin Builder ECE 教程 | `help/ansys-help-topics/TwinBuilder_ECE_Tutorial/` |
