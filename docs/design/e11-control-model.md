# e11 IPM 控制模型 — 设计

> 需求来源：`docs/requirements/e11-control-model.md`（本文逐条对应其 F1–F3）
> 证据分级：**实测** = 本机读文件/跑过；**官方** = Ansys 官方脚本或教程原文；**推断** = 由实测推得，未单独验证。

## 1. 方案与理由

**一句话方案**：参数从 `.mot` 直读 → 用官方 ECE 脚本导出 SML/TXT/MAT → Twin Builder 导入成 ECE 组件承载电机 + 逆变器 → Simulink 只跑控制（FOC + SVPWM + 电流分配），两者以「三相电压指令进、三相电流与转速出」通过 `AnsoftSFunction` 连接。

**为什么电机放 Twin Builder 而不是 Simulink**（用户决定）：ECE 是 FEA 参数化的查表模型，内部已含 Park 变换与磁链/转矩插值（官方教程 §2）。放进 Simulink 需要重写这套插值与电机方程，等于把官方验证过的模型再做一遍；放 Twin Builder 则逆变器与电机在同一求解器里，开关级联立求解不需要跨求解器接口。
代价是 Simulink 侧的线性 dq 电机模型（`PMSM` 模块）用不上，控制器的被控对象只能通过 S-Function 闭环——这与项目已有的 `AnsoftSFunction` 绑定链路（`docs/design/simulink-binding.md`）是同一套。

**为什么控制策略选 FOC + SVPWM**：用户已定。e11 是 8 极 IPM、额定电流 306 A rms、母线 400 V，属于车用大电流低电压平台，SVPWM 相比正弦调制能把线性区电压利用率从 0.612 提到 0.707（`help/ansys-help-topics/BPM_Electromagnetic_Model/BPM_Electromagnetic_Model.md:100`）。

**最近先例**：`docs/design/simulink-binding.md` —— 本项目的 S-Function 绑定与信号映射做法直接复用，不另立接口形态（对齐：`AnsoftSFunction` 块 + `UserData` 绑定 + 端口名约定）。
本项目此前无电机控制模型的先例，故控制侧结构按业界通用 FOC 链路组织（电流环内环 + 速度环外环）。

**公开资料勘察**：已查
`help/repos/pymotorcad/examples/links/ece_export_for_twinbuilder.py`（779 行完整导出脚本，**采用**）、
`help/ansys-help-topics/BPM_Electromagnetic_Model/BPM_Electromagnetic_Model.md`（PWM 调制电压利用率表，**采用**）、
`E:\ANSYS Inc\v261\motorcad\Tutorials\Ansys_TwinBuilder_ECE_Model\TwinBuilder_ECE_Tutorial.pdf`（官方 ECE 教程 42 页，**采用**）、
`help/ansys-help-topics/` 下 Twin Builder 基本元件主题（IGBT/MOSFET 器件模型，供后续功率级使用，本阶段不展开）。

## 2. e11 电机基本参数（F1）

数据源一律为 `models/motorcad/e11_User.mot`（下文坐标均指该文件行号）。

### 2.1 机型与工况

| 项目 | 值 | 坐标 |
|---|---|---|
| 电机类型 | BPM（永磁同步），IPM 内置式转子 | `:61` `Motor_Type=BPM`；模板注记 `IPM`（`:17`） |
| 模板来源 | eMobility 车用，同 e9 设计、转子开槽自适应模板 | `:17` |
| 极数 / 槽数 | 8 极 / 48 槽，q = 2 | `:6571` `Pole_Number=8`；`:6575` `Slot_Number=48` |
| 目标功率等级 | 10,000 rpm（模板注记 120 kW 级） | `:17`；`:5503` `Envelope_Speed_Array[20]=10000` |
| 额定转速（基准） | 6,000 rpm | `:5330` `ShaftSpeed=6000` |
| 母线电压 | 400 V | `:5796` `DCBusVoltage=400`；`:5802` `SupplyVoltage=400` |
| 峰值电流 | 433 A（peak），即 306.2 A rms | `:5780` `PeakCurrent=433`；`:5782` `RMSCurrent=306.177…` |
| 电流定义 | Peak（`CurrentDefinition=0`） | `:5790` |
| 负载工况点（4 点） | 250 rpm/81.6 A → 6000 rpm/82.4 A → 8000 rpm/106.4 A → 10000 rpm/148.9 A，均 40 N·m | `:5430-5449` |
| 对应相角 | 19.44° / 19.69° / 54.51° / 69.02°（电流超前角） | `:5434-5437` |
| 堵转—峰值转矩包络 | 0 rpm 273 N·m → 8000 rpm 155 N·m → 10000 rpm 117.6 N·m | `:5510-5530` |
| 工作温度设定 | 绕组 65 ℃ / 磁钢 65 ℃ | `:6010`；`:6030` |

**关于 40 N·m 工况点**：`.mot` 里的 4 个负载点都是 40 N·m，这是模板自带的算例设定，不代表电机额定点。
真实额定转矩需按 `Envelope_Torque_Array`（`:5510-5530`）与热约束另行确认——本清单只记录文件事实，不据此推断额定点（**未定，见 §8**）。

### 2.2 定子几何

| 项目 | 值 | 坐标 |
|---|---|---|
| 定子外径 | 198 mm | `:6412` |
| 定子内径（bore） | 132 mm | `:6563` |
| 轴向长度 | 260 mm | `:6574` `Motor_Length=260` |
| 槽数 | 48 | `:6575` |
| 槽型 | 平行齿（Slot Type Parallel Tooth），平行槽底 | 界面 `Slot Type Parallel Toc…`（用户截图） |
| 槽底宽 / 槽顶宽 | 6.614 / 4.315 mm | `:6414` `Slot_Width_Bottom`；`:6415` `Slot_Width_Top` |
| 定子材料 | M250-35A 硅钢 | `:4989-4991` |

### 2.3 转子与磁钢

| 项目 | 值 | 坐标 |
|---|---|---|
| 极数 | 8 | `:6571` |
| 转子直径 / 轴径 | 130 mm / 80 mm | 界面（用户截图）；`:6559` `Shaft_Dia=80` |
| 气隙 | 1 mm | `:6572` |
| 磁钢层数 | 1 | 界面 `Magnet Layers=1`（用户截图） |
| 磁钢厚度 / 宽度 | 4 mm / 45 mm | `:6747` `Magnet_Thickness=4`；`:6765` `Magnet_Width=45` |
| 磁桥厚度 | 2 mm | `:6757` `Bridge_Thickness=2` |
| 磁钢材料 | **N30UH**（钕铁硼，UH 耐温等级） | `:5034` `Material_Magnet=N30UH` |
| 磁钢牌号数据 | 在 `.mot` 末尾以材料段内嵌：`[N30UH]`（`:12868` 起） | `:12868` |
| 转子斜极 | 5 段，−3° … +3°，连续斜极 | `:5887-5892`；`:5852` `ContinuousSkewMethod=1` |
| 定子斜槽 | 无（0°） | `:5886` `StatorSkew=0` |
| 对称设置 | `MagneticSymmetry=1`（Full Machine） | `:6057`；`:6058` `MagneticSymmetryFactor=8` |

`MagneticSymmetry=1` 与 `MagneticSymmetryFactor=8` 同时存在：前者是模板保存的完整机状态，后者是磁路对称因子。故障样机导出 Maxwell 时必须保持 Full Machine——这是 `AGENTS.md` 的硬约束，本阶段不触碰。

### 2.4 绕组

| 项目 | 值 | 坐标 |
|---|---|---|
| 绕组型式 | 分布式、重叠绕组（Overlapping），单层 | `:1375` `Winding_Type=Overlapping`；`:5904` `WindingLayers=1` |
| 每槽导体数 | 108 | `:1317` `ConductorsPerSlot=108` |
| 每导体股数（匝） | 6 | `:5922` `MagTurnsConductor=6` |
| 并联支路 | 2 | `:5931` `ParallelPaths=2` |
| 导线 | Metric 表，线径 0.885 mm（铜径 0.8 mm） | `:1373` `Wire_Type=Metric_Table`；`:1306`；`:1301` |
| 每相匝数 | **推断 ≈ 108 × 6 / 2 / 3 = 108**（每槽 108 根导体，每槽两层三相各一相，故每相每槽 36 根；×6 股 ÷2 并联 = 108） | 推断，**未实测** |
| 端部绕组长（MLT） | 178.43 mm | `:1378` `EWdg_MLT=178.429790068625` |
| 槽满率 | 68.3%（槽）/ 端部 46.5% | `:946` `Slot_Fill`；`:1313` `EWdg_Fill` |
| 铜材料 | Copper (Pure) | `:4992` |

每相匝数的推算是本清单里唯一不能直读的量，控制模型需要它换算磁链—电流关系，故须在 §8 列为待实测项。

### 2.5 驱动与调制（Motor-CAD 内部设置）

| 项目 | 值 | 坐标 |
|---|---|---|
| 驱动类型 | 正弦驱动（Sine），3 相 | `:17` `Sine`；`:5850` `BPMDriveMode=0` |
| 调制方式 | 驱动器调制 `DriveModulation=0` | `:5797` |
| 等效开关频率 | 100 kHz（Motor-CAD 计算用） | `:5807` `DriveEffectiveSwitchingFrequency=100000` |
| 开关管压降 / 二极管压降 | 0.8 V / 0.6 V（Motor-CAD 电路损耗用） | `:5804`；`:5806` |
| 开关电阻 | 0（理想） | `:5798` |
| 母线内阻 / 电容 | 0 / 0（理想源） | `:5801`；`:5803` |
| SVPWM 增益因子 | 0.1（Motor-CAD 内部空间矢量驱动参数） | `:5810` `SpaceVectorDriveGainFactorG2=0.1` |

`:5807` 的 100 kHz 是 Motor-CAD 在算损耗时用的等效开关频率，不是逆变器真实开关频率。真实开关频率属功率级设计参数，Simulink 侧 SVPWM 的载波频率须单独给定（§8）。

### 2.6 ECE 提取所需的输出量（跑 Motor-CAD 才能拿到）

以下量不在 `.mot` 里，必须由 Motor-CAD 计算后 `get_variable` 读取（官方脚本 `ece_export_for_twinbuilder.py:308-309`）：

- `ArmatureWindingResistancePh` —— 每相电阻（Ω）
- `EndWdgInductance_Used` —— 端部绕组电感（H）
- `DriveOffsetAngleLoad` —— 驱动对齐角（电角度）

## 3. 控制模型需要什么（F3）

### 3.1 控制结构选择

| 策略 | 是否需要 | 理由 |
|---|---|---|
| FOC（磁场定向，dq 电流闭环） | **要** | 用户已定；IPM 的转矩依赖 d/q 双电流，标量控制不适用 |
| SVPWM | **要** | 用户已定；400 V 母线 + 306 A rms 的电流等级，需最高电压利用率 |
| MTPA | **要**（作为电流分配表） | IPM 有磁阻转矩（Ld ≠ Lq），id = 0 会浪费磁阻分量。用查表形式实现，不解析求导 |
| 弱磁（FW）/ MTPV | **要，本阶段纳入**（用户 2026-10-20 决定提前） | 满载基速约 4,040 rpm，.mot 的 6,000 rpm 负载点已在弱磁区；见 §3.2 |

**MTPA 的实现口径**：e11 的 Ld/Lq 差值需由 ECE 饱和图给出（`Angular_Flux_Linkage_D/Q`），因此 MTPA 表的输入是 (Te*, ω)，输出是 (id*, iq*)，在 Simulink 里用 1-D/2-D Lookup Table 实现。ECE 数据本身就带转矩对电流的映射，可直接由它反查 MTPA 工作点，不需要另建解析模型。

### 3.1.1 ECE 实测数据结论（e11，61×61 电流网格 × 41 位置点）

> 数据源 
esults/e11-ece-61x61/ECE_e11_61x61_map.mat（2026-10-21 计算，243.5 min）。
> 粗网格曾有两个坑：Ld/Lq 字段在零电流处是除零产物（读到 -7.4e13），且其量纲与 arUnits 标称不符。
> **电感一律由磁链反推**：Lq = λq/iq（Id=0 时）、Ld = (λd − λpm)/id（Iq=0 时）。

| 量 | 取值 | 来源 |
|---|---|---|
| 永磁磁链 λpm | **0.075883 Wb** | Flux_Linkage_D(Id=0, Iq=0) |
| Ld | **226 µH**（Id=−433 A）／162 µH（Id=+433 A）／242 µH（近零电流） | 磁链反推 |
| Lq | **297 µH**（|Iq|=433 A）／665 µH（|Iq|=58 A） | 磁链反推 |
| 凸极率 Lq/Ld | **约 1.3**（额定电流）／约 2.7（轻载） | 由上面两项相除 |
| 每相电阻（65 ℃） | **13.38 mΩ** | ArmatureWindingResistancePh |
| 端部电感 | **6.03 µH** | EndWdgInductance_Used |

**e11 是标准 IPM 凸极（Ld < Lq）**。这不是异常：IPM 的磁钢埋在转子内，d 轴磁路被磁钢（磁导率≈空气）堵住，
所以 Ld 小于 Lq。MathWorks 的 MTPA 公式直接以 Lq > Ld 为前提书写。

**转矩方向核对**：Te = 1.5·p·[λpm·iq + (Ld − Lq)·id·iq]。因 Ld < Lq，第二项在 id<0、iq>0 时为**正**——
负 Id 增转矩、正 Id 削转矩，与实测一致（Id=+216.5、Iq=324.75 时转矩只剩 25.2 N·m）。

**433 A 电流圆内最优点**（61×61 网格实测）：

| 工作点 | Id (A) | Iq (A) | 电流 (A) | 转矩 (N·m) |
|---|---|---|---|---|
| id = 0 控制 | 0 | 433 | 433 | 161.7 |
| MTPA 实测点 | **−303.1** | **303.1** | 429 | **246.4** |

MTPA 比 id=0 多出约 **52%** 转矩（同电流圆内）。粗网格（9×9）只能找到 219.6 N·m，
密度不够——这也是改用 61×61 的原因。

**基速**：按 max = Vdc/√3 = 230.9 V（SVPWM 线性区相电压峰值），
ωbase = vmax / |λ| / p，代入满载磁链模值约 0.137 Wb：

| 工况 | 磁链模值 | 基速 |
|---|---|---|
| 满载（Iq≈433 A） | 0.137 Wb | **约 4,040 rpm** |
| 轻载 | 更低 | 更高 |

基速随负载变化，**不能当成固定转速阈值**：判据应写成 |λ| ≤ vmax/ωe。

**ECE 查表的物理量**（
esults/e11-ece-61x61/ECE_e11_61x61_txt_file.txt）：157,604 行 = 61 × 61 × 41，
每行「索引 / Ψd / Ψq / Ψ0 / 转矩」。位置序列从对齐角 90° 电角起步往后退 41 点（电角 90° → 0°），
负索引按**周期 120 点**回绕（不按样本数 121，后者会落到 360° 的重复样本上，整体错位一格）。

### 3.2 弱磁与 MTPV 的设计口径

**为什么必须做**：电压极限 `|ψ| ≤ Vmax/ωe` 随转速反比收缩。ECE 饱和图给出的磁链范围是
ψd ∈ [−0.022, 0.146]、ψq ∈ [−0.137, 0.137] Wb，而电压限在各转速下的允许模值：

| 转速 | ωe (rad/s) | \|ψ\| ≤ | 说明 |
|---|---|---|---|
| 3,000 rpm | 1,257 | 0.260 Wb | MTPA 区，电流限约束为主 |
| 5,000 rpm | 2,094 | 0.156 Wb | 接近边界，仍可 MTPA |
| 6,000 rpm | 2,513 | 0.130 Wb | 须弱磁 |
| 8,000 rpm | 3,351 | 0.098 Wb | 深度弱磁 |
| 10,000 rpm | 4,189 | 0.078 Wb | ψf 自身 0.0759 Wb，几乎无裕量 → MTPV |

**四个区的划分**（电流限圆 `Is ≤ Imax` 与电压限椭圆 `|ψ| ≤ Vmax/ωe` 的交集）：

| 区 | 判据 | 电流分配规则 |
|---|---|---|
| Ⅰ MTPA | 电压椭圆完全包住电流圆 | 沿 MTPA 轨迹取点（§3.1.1 第 1 条） |
| Ⅱ 弱磁（恒转矩） | 电流圆与电压椭圆相交 | 沿电流圆边界，Id 往负方向加，直到椭圆边界 |
| Ⅲ 弱磁（恒功率） | 同上，且转矩指令随转速反比下降 | 沿椭圆边界与电流圆边界的交点 |
| Ⅳ MTPV | 电流圆边界已不可达 | 沿 MTPV 轨迹（dψ/dθ 最大转矩方向） |

**实现口径**：不做解析弱磁公式（电压方程 + 饱和查表求根，实时算不稳），
改成**离线生成 (Te*, ω) → (Id*, Iq*) 二维查表**，Simulink 里就是一张 2-D Lookup Table：

1. 在 ECE 网格上对每个 (Id, Iq) 点算出 T 与 |ψ|；
2. 对每个转速 ωe，把 |ψ| ≤ Vmax/ωe 的点筛出来，在其中取 T 最大的点；
3. (Te*, ω) → 该点 (Id*, Iq*) 即弱磁表的表值；
4. 表外（超出可达转矩）线性外推并置饱和，由电压环兜底。

**电压环兜底**：查表之外再加一个 PI 电压环——检测 `|Vdq|` 超过 `0.95·Vmax` 时，把 Id* 往负方向推。查表负责稳态轨迹，电压环负责抑制参数误差与瞬态。两者叠加是标准做法，单独用哪个都有缺口（只查表则扰动下易超压，只电压环则稳态轨迹不最优）。

**本设计能做到的边界**：10,000 rpm 下 |ψ| 上限 0.078 Wb 与 ψf 持平，
MTPV 段的可输出转矩会很小（由 ECE 数据算出，见 §3.3）；若实际需要高速大转矩，得改电机设计（减 ψf 或加深磁路），不是控制能补的。

### 3.3 弱磁表的数据来源

弱磁表**不能从 8×8 网格插出**：MTPV 轨迹落在电流圆边缘、电压椭圆的切点上，
8 点/轴的分辨率（步长 108 A）误差可达数十安培。因此：

| 用途 | 数据集 |
|---|---|
| MTPA 主表 | `results/e11-ece/`（9×9 × 41，已产出） |
| 弱磁 / MTPV 表 | `results/e11-ece-20x20/`（20×20 × 41，本批产出） |

20×20 的步长 45.58 A，对 MTPV 轨迹够用；40×40 会到 22 A 但耗时翻四倍，暂无必要。

### 3.4 Simulink 控制模型结构

```
   速度环 PI ─► Te* ─► 电流分配表 ─► Id*, Iq* ─► 电流环 PI(dq) ─► 反 Park ─► SVPWM ─► 六路 PWM ─┐
      ▲                    ▲              ▲                  ▲                                 │
      │                    │              │                  │                                 ▼
   ω (反馈)          ω, |Vdq|★       id,iq (反馈)       Park 变换 ◄──── ia,ib,ic ◄──── S-Function(TB)
                                                          ▲
                                            转子电角度 θe ◄──── 机械角 / 转速

   ★ 电压环兜底：|Vdq| > 0.95·Vmax 时把 Id* 往负方向推（§3.2）
```

**电流分配表（核心）**：一张 2-D Lookup Table，输入 (Te*, ω)、输出 (Id*, Iq*)。
表值由 ECE 数据离线生成（§3.2 的四个区 + §3.3 的数据源），运行时不求根。

外环：转速 PI → 转矩指令 Te*。内环：dq 电流 PI。前馈：反电动势项 ωe·ψ 由 ECE 的 Ψd/Ψq 查表给（可选，先不做）。

**与无弱磁版的差别**：原设计只有「速度环 → MTPA 表」，现在 MTPA 表升级为覆盖四个区的电流分配表，并多一个电压环兜底支路。SVPWM 与电流环不受影响。

### 3.5 接口定义：Simulink ⇄ Twin Builder

ECE 组件在 Twin Builder 侧的引脚（官方 SML `ece_export_for_twinbuilder.py:526-533` 与教程 §6）：

| ECE 引脚 | 类型 | 含义 |
|---|---|---|
| A0 / B0 / C0 | electrical | 三相绕组端（接逆变器桥臂中点） |
| X0 / Y0 / Z0 | electrical | 三相绕组中性点端（星点，通常并一起接地） |
| ROT1 / ROT2 | rotational_V | 机械端口（接负载/转速源） |
| ra0, la0 | 参数 | 相电阻、端部电感 |
| Fluxd0 / Fluxq0 / Fluxa0… | 输出 | dq 与三相磁链 |
| Pos | 输出 | 机械角位置（deg） |

**Simulink 侧的端口**（对应 `AnsoftSFunction` 的 `SimulinkName` / `SimulinkDirection`）：

| 信号 | 方向（Twin Builder → Simulink 记 0；Simulink → Twin Builder 记 1） | 单位 | 物理含义 |
|---|---|---|---|
| `uA` / `uB` / `uC` | 1（Simulink → TB） | V | 三相桥臂中点对直流母线中点电压指令 |
| `iA` / `iB` / `iC` | 0（TB → Simulink） | A | 三相电流 |
| `wm` | 0 | rad/s 或 rpm（待定，§8） | 机械转速 |
| `Te` | 0 | N·m | 电磁转矩（观测/前馈用） |
| `TL` | 1 | N·m | 负载转矩（若负载在 Simulink 侧给定） |

**方向约定已由项目既有实测确认**：`docs/design/simulink-binding.md:363` 给出 `uA,uB,uC,TL` 方向 1、`iA,iB,iC,wm,THM,Te` 方向 0，与上表一致。

**为什么是「电压指令进」而不是「开关信号进」**：SVPWM 在 Simulink 侧生成占空比，Twin Builder 侧只接收等效电压或直接接收六路 PWM。
两种都可行，差别是开关管是否要被跨求解器驱动——若 TB 侧收 PWM，则开关器件在 TB 中按真实门极驱动模型动作，损耗与死区可算；若收电压，则 TB 侧需要一个受控电压源，开关损耗需另算。**本设计取「TB 侧收 PWM、Simulink 出六路门极信号」**，理由是用户明确要把开关管放 Twin Builder，门极信号是唯一的自然接口（§8 列了改回电压接口的代价）。

## 4. ECE 提取流程（F2）

### 4.1 用哪份脚本

| 脚本 | 位置 | 差异 | 选用 |
|---|---|---|---|
| PyMotorCAD 官方示例 | `help/repos/pymotorcad/examples/links/ece_export_for_twinbuilder.py` | 自起新 Motor-CAD 实例，全部参数来自 JSON | **采用** |
| Motor-CAD 安装目录教程版 | `V261\motorcad\Tutorials\Ansys_TwinBuilder_ECE_Model\MotorCAD_ECE_Export.py` | 连接已开实例（`open_new_instance=False`），参数硬编码 | 备用（调试时连 GUI） |
| MATLAB 版 | 同目录 `MotorCAD_ECE_Export.m` | 同逻辑 | 不用（项目以 Python 为主线） |

### 4.2 配置（`ece_config.json` 口径，改 e11）

官方示例的配置项见 `ece_config.json` 与教程 §5。e11 的取值：

| 键 | 官方 e8 默认 | e11 取值 | 依据 |
|---|---|---|---|
| `mot_file` | `e8_eMobility.mot` | `e11_User.mot` | 用户指定 |
| `shaft_speed` | 3000 | **6000** | `.mot:5330` 基准转速；教程建议取低于基速的值。6,000 rpm 下单载反电势 191 V，为线性调制上限 326.6 V 的 59%，仍在线性区；选它是为了与 .mot 的负载点保持同一转速基准 |
| `dc_bus_voltage` | 350 | **400** | `.mot:5796` |
| `machine_temp` | 75 | **65** | `.mot:6010`/`:6030` 当前工作温度 |
| `Id_max` | 250 | **433** | `.mot:5780` 峰值电流；教程建议取电源最大电流以保证大电流精度 |
| `current_step` | 50 | **50**（待定） | 433/50 ≈ 8.7 点/轴；教程建议 ≥20 点，故宜取 **21.65**（433/20）由 8.7 提到 20 点，见 §8 |
| `torque_points_per_cycle` | 30 | 脚本自动重算 | `ece_export_for_twinbuilder.py:273-296` 按对齐角求因式分解，脚本会覆盖 |

### 4.3 产出物

跑完得到三个文件，全部落在脚本同目录的 `Results/` 下（`ece_export_for_twinbuilder.py:142-150`）：

| 文件 | 内容 |
|---|---|
| `ECE_e11_map.mat` | 饱和图原始数据：`Id_Peak` / `Iq_Peak` / `Angular_Flux_Linkage_D` / `_Q` / `_Phase_1..3` / `Angular_Rotor_Position` / `Angular_Electromagnetic_Torque` / `Phase_Advance`（`:370-379`） |
| `ECE_e11_txt_file.txt` | 文本表：极数、每相电阻与端部电感、Id/Iq 扫描点、转速角点、dq 磁链与转矩矩阵（`:506-514`） |
| `ECE_e11_sml_file.sml` | Twin Builder 模型定义：ECE 组件端口、内部 Park 变换网络、NDSRC 查表（`:524-707`） |

### 4.4 导入 Twin Builder

`Tools → Project Tools → Import Twin Builder Models` → 选 SML → 组件出现在 `Component Libraries / Project Components`（教程 §5；`ece_export_for_twinbuilder.py:748-751`）。
之后按 `Edit Symbol → Edit Pin Locations` 把 A0/B0/C0/ROT2 放左、X0/Y0/Z0/ROT1 放右（`:762-765`）。

### 4.5 已知风险（均已实测复现并处置）

| 风险 | 实测表现 | 处置 |
|---|---|---|
| **气隙网格未开** | `AnsysAirgapMesh=0` 时饱和图报 `Mesh17:IntRadius and ExtRadius must be defined if air_gap is not meshed` 与 `MeshRotate: (UEM) Undefined airgap region`，随后 `EAccessViolation` 崩溃，整批算空 | `ensure_airgap_mesh()` 在计算前强制置 1 并回读确认（`AGENTS.md` 已记该约束） |
| 饱和图是异步启动 | `calculate_saturation_map()` 立刻返回一句 `Lab is already running`——那是「已启动」回执，不是失败 | 不当失败处理，改为轮询 `SaturationMap_CalculationComplete`；不靠 `SaturationMapRunning`（实测它从不清位为 True） |
| 位置点数与推算不符 | `360/步长 = 120`，但 MAT 实际给 121 点（0..360 含首尾） | 查表周期长度按 MAT 实际 `shape[2]` 取，不按推算值 |
| 缺少 scipy | 读 MAT 时报 `ModuleNotFoundError: No module named 'scipy'` | 已装 scipy 1.18.1 到 `pmsm` 环境 |
| 饱和图算得慢 | 实测 9×9 电流 × 121 位置 = 81 个负载点，耗时 311 s（14 核并行） | 已可接受；加密到 20×20 约需 20 分钟 |
| `.mot` 被脚本改写 | 脚本会 `save_to_file` 回写 MOT（官方 `:226`、`:345`） | 入口先复制到 `results/e11-ece/work/`，原文件全程只读 |

## 5. 目录与产物

```
config/cases/e11_ece_config.json       ← e11 的 ECE 配置（从官方 ece_config.json 派生）
scripts/run_ece_export.py              ← 入口：读配置 → 调 ECE 导出 → 落到 results/
src/motorcad_controller/ece_exporter.py ← ECE 导出逻辑（从官方脚本抽取为可测函数）
results/e11-ece/                       ← SML/TXT/MAT 产物归档
models/simulink/e11_control.slx        ← 控制模型（F3，第二阶段）
```

`src/motorcad_controller/` 在 `AGENTS.md` 中已规划为预留目录，本批次正式启用。

## 6. 验收标准

| 需求 | 验收命令 / 判据 |
|---|---|
| F1 | 本文 §2 每条带 `file:line`；每相匝数等推断项明确标「推断/未实测」 |
| F2 | `results/e11-ece/` 下三个文件存在；SML 中 `MODELDEF ECE_e11` 起、`PORT electrical: A0;` 至 `PORT ROTATIONAL_V: ROT2;` 八端口齐全；TXT 中 `B_BasicData` 段 `Poles 8` |
| F3 | 接口表 §3.3 五个信号方向与 `simulink-binding.md:363` 实测一致；控制模型能在 6000 rpm / 40 N·m 工况下收敛 |

单行宽 ≤ 300 字符（与项目 `checkConfig.lineWidth` 一致）。

## 7. 需要用户决定的三项

| # | 选择 | 选项 | 我的建议 |
|---|---|---|---|
| 1 | 控制策略档位 | (a) 只做 FOC+SVPWM，id = 0；(b) FOC+SVPWM+MTPA 查表 | (b)——IPM 必须用磁阻转矩，但 MTPA 表要先有 ECE 数据，所以是「先 (a) 跑通、再补 (b)」 |
| 2 | 弱磁是否本阶段做 | (a) 不做；(b) 加弱磁到 10,000 rpm | 已判：（b）提前纳入。满载基速约 4,040 rpm，6,000 rpm 负载点已在弱磁区，不做弱磁到不了 `.mot` 的工况点 |
| 3 | ECE 提取的电流网格 | 20×20 点（约 12,000 次 FEA）/ 8×8 点（先跑通） | 先用 8×8 跑通全链路验证接口，再决定是否加密 |

## 8. 未决项与现在不能定的原因

| 未决项 | 为什么现在不能定 |
|---|---|
| 每相匝数 | `.mot` 只有 `ConductorsPerSlot=108`、`MagTurnsConductor=6`、`ParallelPaths=2`，缺绕组层与相数在槽内的分配口径；推得 108 匝但未实测。须连 Motor-CAD 用 `get_variable` 读或看 Winding 界面确认 |
| 真实额定转矩 / 额定点 | `.mot` 的 4 个负载点都是 40 N·m（模板算例），并非设计额定点；包络曲线最大值 273 N·m。控制模型的速度环增益需要额定转矩才能定标 |
| d/q 电感基准值 | 由磁链反推：Ld 226 µH（Id=−433 A）／242 µH（近零电流），Lq 297 µH（|Iq|=433 A）／665 µH（轻载）。MAT 的 `Ld`/`Lq` 字段在零电流处是除零产物，不可直接引用。控制表用查表，不取单一基准值 |
| 开关频率 | Motor-CAD 的 100 kHz 是损耗等效频率，不是逆变器实际载波频率；SVPWM 载波须按功率级设计给定 |
| `wm` 单位 | Twin Builder 转速端口是 rad/s 还是 rpm 未核实；`simulink-binding.md:363` 只记录了端口名 `wm`，无单位 |
| 弱磁起始转速 | 满载约 4,040 rpm（`results/e11-ece-61x61/` 实算）。该值是负载相关量，控制侧以 `|λ| ≤ vmax/ωe` 在线判定，不写死转速 |
| 逆 Nord 极性 / 电流正方向 | 逆变器电流正方向与 ECE 绕组电流正方向需在联合仿真首次对齐时用开路反电势波形确认 |
