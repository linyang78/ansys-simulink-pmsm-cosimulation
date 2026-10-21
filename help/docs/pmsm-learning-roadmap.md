# PMSM 电机控制学习路线图（Roadmap）

> 配套材料：`mathworks/` 下 20 篇官方文档存档 + `pmsm-knowledge-map.md`（知识点图谱）
> 制定日期：2026-10-21 · 文档版本 R2026b
> 适用对象：有电路/控制基础、想系统掌握 IPMSM 磁场定向 + MTPA + 弱磁控制，并能落到 Simulink/硬件上的学习者
> 总周期：约 8–10 周（每周 8–10 小时）；可按「速成版」压缩到 4 周（跳过 ★ 标记内容）

---

## 0. 先修检查（不满足就先补，1–3 天）

开始前请确认自己能回答：

- [ ] 三相电机的转矩为什么和电流「相位」有关？为什么不能直接调三相正弦电流？
- [ ] 什么是 dq 轴？为什么旋转坐标系能把交流量变成直流量？
- [ ] PI 控制器的 Kp/Ki 分别影响什么？积分饱和是什么？
- [ ] 什么是标幺制？为什么要用？
- [ ] Simulink 基本操作：子系统、采样时间、Scope/Data Inspector

**补课材料**（不在本档案馆，按需外链）：
- 电机学基础：任意一本《电机学》的同步电机章节（重点是凸极、磁阻转矩）
- 自动控制原理：一阶/二阶系统、PI 调节、频域带宽概念
- Simulink Onramp（MathWorks 官方免费交互课程）

> ⚠️ 如果「磁阻转矩」和「dq 变换」两个概念完全陌生，不要跳过先修——后面所有公式都会变成背诵。

---

## 1. 学习路径总览

```
阶段 0  建立全景        ── 1 天   ── 知道地图长什么样
阶段 1  电机本体+数学模型 ── 1 周   ── 能推 dq 方程、画约束曲线
阶段 2  变换+标幺       ── 1 周   ── 能手算 Clarke/Park、会设基准值
阶段 3  FOC 控制环      ── 2 周   ── 能搭出双环并解释每个模块
阶段 4  MTPA+弱磁       ── 2 周   ── 能画三段轨迹、解释三种 FW 方法
阶段 5  参数估计+整定    ── 1 周   ── 能算增益、能上板估参数
阶段 6  非线性 LUT 实战  ── 2 周   ── 能建 e11 的 LUT 并跑通仿真
阶段 7  部署与验证       ── 1 周   ── 能生成代码、上板、排故
```

每个阶段的固定结构：**目标 → 必读（按顺序）→ 动手 → 验收标准 → 常见坑**。

---

## 阶段 0：建立全景（1 天，2–3 小时）

### 目标
知道 PMSM 控制这门学问由哪几块组成，以及每块在哪个文档里。

### 必读
1. `pmsm-knowledge-map.md` §1 七层总览 + §4 FOC 数据流图（20 分钟）
2. `mathworks/field-oriented-control.zh-CN.md` 通读一遍，不求懂细节（40 分钟）
3. `mathworks/README.md` 文件清单，知道手上有哪些弹药（10 分钟）

### 动手
- 在纸上默画 FOC 数据流图：转速环 → 参考电流 → 电流环 → 电压 → PWM → 电机 → 反馈
- 标出图里每一处「你还不懂」的地方，那就是后面阶段的目标

### 验收标准
- [ ] 能不看文档说出 FOC 的双环结构、内外环速率关系
- [ ] 能说出 Clarke/Park 各自把什么变到什么
- [ ] 知道 MTPA 和弱磁分别解决什么问题

---

## 阶段 1：电机本体与数学模型（1 周）

### 目标
从「电机是什么」推到「dq 方程 + 约束曲线 + 基速」，能自己算出一台电机的运行边界。

### 必读（严格按顺序）
1. `mathworks/pmsm-characteristics-constraint-curves.md` §PMSM 类型与 d-q 轴、转折转速与基速
   —— 先建立 SPMSM/IPMSM、凸极、基速的直觉
2. `mathworks/mtpacontrolreference.zh-CN.md` §PMSM 的数学模型 + §基转速
   —— 逐行抄写 dq 方程、转矩方程、基速公式到笔记本
3. `mathworks/sq-pmsm-block.md` §方程 / Park 变换后的简化方程
   —— 看模块级实现，注意 Park 变换的「非正交」约定
4. `mathworks/pmsm-characteristics-constraint-curves.md` §三条约束曲线 + §三个运行段
   —— 结合公式理解电流圆、电压椭圆、MTPV

### 动手实验
**实验 1.1 手算基速**
用文档里的 BLY171D 参数（p=4, Rs=0.45, Ld=1e-3, Lq=1.4e-3, λpm=5.2e-3, Vdc=24, Imax=2）：
- 手算 ωbase（用 `ωbase = (1/p)·vmax/sqrt((Lq·iq)² + (Ld·id+λpm)²)`）
- 在 MATLAB 里跑 `mcb.PMSMSpeeds` 对照，误差应 < 2%
- 把 Lq/Ld 从 1.4 改到 1.0（变成 SPMSM），观察基速与转矩变化

**实验 1.2 画约束曲线**
- 跑 `mcb.PMSMCharacteristics(pmsm, inverter, 'driveCharacteristics', 2, 'constraintCurves', 1)`
- 截图并在图上标注：电流极限圆、电压椭圆、MTPA 轨迹、MTPV 轨迹、三个里程碑点
- 改 `FWCMethod` 为 `cvcp`/`cccp`/`none`，对比里程碑转速表（理解四种策略差异）

**实验 1.3 实际 vs 近似方程**
- 用 `'voltageEquation','actual'` 与 `'approximate'` 各算一次最高转速
- 记录差值百分比，解释为什么高速时 i×r 项不能忽略

### 验收标准
- [ ] 能默写 dq 电压方程、磁链方程、转矩方程（含磁阻转矩项）
- [ ] 能解释「为什么 IPMSM 的 Lq > Ld 就有磁阻转矩」
- [ ] 能画出一张完整的 id-iq 平面约束图，标出三个运行段
- [ ] 能解释基速、转折转速、里程碑转速三者的关系
- [ ] 能说出 VCLMT / CVCP / CCCP / NONE 四种弱磁策略的区别

### 常见坑
- 把「电角速度 ωe」和「机械角速度 ωm」混用（差 p 倍）
- 电压椭圆中心是「特征电流」点，不是原点
- 忽略 Rs 导致高速转速算偏高（文档实测差 6.8%）

---

## 阶段 2：坐标变换与标幺制（1 周）

### 目标
能手算 Clarke/Park，理解标幺制的每个基准值从哪来、为什么这么取。

### 必读
1. `mathworks/open-loop-and-closed-loop-control.md` §矢量控制
   —— Clarke/Park 的动机：为什么 PI 控直流量效率高
2. `mathworks/field-oriented-control.zh-CN.md` §磁场定向控制算法
   —— 三个坐标系的物理图像
3. `mathworks/per-unit-system.md` 全文
   —— 重点：V_base 随 PWM 方式变、I_base=ISenseMax、T_base 公式、峰值 vs 有效值

### 动手实验
**实验 2.1 手算一次变换**
取 ia=1, ib=−0.5, ic=−0.5（幅值 1 的三相平衡），θe=30°：
- 手算 Clarke → αβ，再 Park → dq
- 用 `Clarke Transform` / `Park Transform` 模块搭最小模型验证
- 故意用「等功率变换」系数再算一次，记录差异（理解 2/3 归一化约定）

**实验 2.2 标幺制换算表**
以 e11 为例填表：

| 量 | 公式 | 数值 |
|---|---|---|
| V_base | Vdc/√3（SVPWM） | 400/√3 = 230.94 V |
| I_base | 逆变器 ISenseMax | 待定（建议 433 A 峰值） |
| N_base | 满载基速 | ≈ 4040 rpm |
| T_base | 1.5·p·λpm·I_base | 1.5×4×0.075883×433 ≈ 197.1 N·m |
| P_base | 1.5·V_base·I_base | ≈ 150.0 kW |

- 用 `mcb.getPUSystemParameters(pmsm, inverter)` 验证
- 跑一个 SI 模型和一个 PU 模型，对比控制器响应应完全一致

### 验收标准
- [ ] 能徒手完成 3→2→dq 的一次完整变换（含数值）
- [ ] 能解释为什么 SVPWM 的 V_base 是 Vdc/√3 而不是 Vdc/2
- [ ] 能说出 T_base 为什么「数学上存在但物理上不一定可达」
- [ ] 能列出把 SI 模型改成 PU 模型要动的 7 个地方

### 常见坑
- V_base 多乘 √2（本档案馆 `per-unit-system.md` 有专门警示）
- I_base 用电机峰值电流代替逆变器采样量程
- 忘记 PU 下 PI 限幅要改成 ±1

---

## 阶段 3：FOC 控制环（2 周）

### 目标
能独立搭出一个能转的 FOC 双环模型，并解释每个模块的作用与参数。

### 必读（按顺序）
1. `mathworks/field-oriented-control.zh-CN.md` §对 FOC 算法进行建模（重读，这次看细节）
2. `mathworks/design-field-oriented-control-algorithm.md`（五步工作流总纲）
3. `mathworks/design-current-controller.md`（第 2 步详展：双 PI + 三变换 + PWM）
4. `mathworks/field-oriented-current-controller.md`（成品模块：端口/饱和方法/PWM）
5. `mathworks/open-loop-and-closed-loop-control.md` §开环到闭环的切换
6. `mathworks/gain-calculation-and-tuning.md`（整定顺序）
7. ★ `mathworks/creating-plant-model.md`（要自己搭对象时读）

### 动手实验
**实验 3.1 从零搭电流环（不用成品模块）**
按 `design-current-controller.md` 的 7 步：
- 两个 PI（d/q）+ Clarke/Park/反 Park + PWM Reference Generator
- 用 `mcb_pmsm_foc_system` 里的对象模型或自己搭的 RL 负载
- 给 id_ref=0.2, iq_ref=0.5 阶跃，观察 id/iq 跟踪（应无稳态误差）
- 记录上升时间，与理论带宽对比

**实验 3.2 用成品模块复现**
- 换成 `Field-Oriented Current Controller` 模块，参数一致
- 对比两者波形（应基本重合）——理解模块内部就是实验 3.1 的结构
- 改 `Saturation method` 三种取值，观察电压饱和时的行为差异

**实验 3.3 转速外环**
- 加转速 PI（带宽取电流环的 1/5–1/10）
- 阶跃给定 1000→2000 rpm，观察转速响应与 iq 指令
- 加负载转矩阶跃，观察转速跌落与恢复

**实验 3.4 开环启动**
- 先开环 V/F 拖动到 10% 基速，再切闭环（PI 初值 = 开环输出）
- 对比「直接闭环启动」与「开环切闭环」的电流冲击

### 验收标准
- [ ] 能不看文档说出电流环的完整信号链（含每个变换的方向）
- [ ] 能解释 PI 限幅为什么取 Vdc/√3（SVM）
- [ ] 能解释为什么转速环必须比电流环慢
- [ ] 能说清开环切闭环时 PI 复位的作用
- [ ] 模型能稳定跟踪转速阶跃，超调 < 10%，无持续振荡

### 常见坑
- 电流环采样周期与控制周期不一致（Function-Call 调度错）
- Park 变换角度用机械角而非电角度（差 p 倍）
- 反 Park 后忘记归一化到占空比 0–1
- 转速环 PI 限幅没设成 ±I_max

---

## 阶段 4：MTPA 与弱磁（2 周）

### 目标
理解「同样电流怎么出力最大」「超过基速怎么继续加速」，能解释三种弱磁策略并复现轨迹。

### 必读（按顺序）
1. `mathworks/mtpacontrolreference.zh-CN.md` §内置式 PMSM（MTPA + VCLMT 公式组）
2. `mathworks/field-weakening-control-mtpa-pmsm.zh-CN.md` 全文
   —— 弱磁的物理直觉、MTPA 的效率意义、三种参考电流生成法
3. `mathworks/pmsm-characteristics-constraint-curves.md` §三个运行段（重读，这次带公式）
4. `mathworks/lut-based-pmsm-control-reference.md` §描述（四种输入方式的解算逻辑）

### 动手实验
**实验 4.1 验证 MTPA 公式**
- 用 IPMSM 参数，在 im=5 A 下用公式算 id_mtpa、iq_mtpa
- 在 id-iq 平面扫描转矩角 β（0→90°），找最大转矩点，应与公式一致
- 对比 id=0 控制与 MTPA 控制的转矩差（文档示例：0.34 PU vs 0.27 PU）

**实验 4.2 三段轨迹**
- 用 `mcb.PMSMSpeeds` 拿到三个里程碑转速
- 在三个转速处各画一张约束图（`opacity` 0.5/0.3 叠加）
- 标出工作点 A→B→C 的移动路径，解释每段受什么约束

**实验 4.3 弱磁仿真**
- 跑 `mcb_pmsm_fwc_qep_f28379d`（或简化版）
- 转速从 0 缓慢升到 1.5 倍基速，观察 id 变负、iq 受限
- 记录转矩-转速曲线，与理论驱动特性对比

**实验 4.4 四种 FW 方法对比**
- 同一电机分别用 vclmt/cvcp/cccp/none，记录最高转速与高速段转矩
- 解释为什么 IPMSM 适合 VCLMT、SPMSM 适合 CVCP

### 验收标准
- [ ] 能写出 MTPA 的 id 公式并解释每一项的来源
- [ ] 能画出三段轨迹图并说出每段的约束边界
- [ ] 能解释「弱磁 = 负 id 抵消永磁磁链」
- [ ] 能说出 CVCP/CCCP/VCLMT 的适用场景
- [ ] 仿真中能观察到基速以上 id < 0 且转速继续上升

### 常见坑
- 弱磁段转速给定一次跳变太大导致失稳（文档建议小步长）
- 忽略温度/电流限值，弱磁时电流超额定
- 把 MTPV 当成「一定能达到」——部分电机只有两个里程碑转速

---

## 阶段 5：参数估计与增益整定（1 周）

### 目标
知道每个参数从哪来、怎么测、怎么算增益，能独立完成一次整定。

### 必读
1. `mathworks/estimate-pmsm-parameters.md`（估计顺序 Rs→Ld→Lq→(Ke,J,B)）
2. `mathworks/estimate-control-gains-and-tune.md`（四种增益路线 + 函数表）
3. `mathworks/gain-calculation-and-tuning.md`（重读，对照函数）

### 动手实验
**实验 5.1 参数估计（有硬件）**
- 按文档跑 `mcb_pmsm_param_est_f28379d`，Manual 模式逐个测
- 记录 Rs/Ld/Lq/Ke/J/B，与数据手册对比
- 故意跳过 Ld 直接测 Lq，观察报错（理解顺序依赖）

**实验 5.2 参数估计（无硬件）**
- 用 `mcb_pmsm_param_est_f28379d` 的仿真模式
- 或直接用数据手册值 + `mcb.getPMSMParameters('BLY171D')`

**实验 5.3 增益计算与验证**
- 用 `mcb.calcFOCGains`（或 `mcb.getPIControllerParameters`）算电流环/转速环增益
- 用 `mcb.getMotorControlAnalysis` 看频域响应（相位裕度 > 45°）
- 把增益代入阶段 3 的模型，验证阶跃响应
- 再用 FOC Autotuner 整定一次，对比两组增益

### 验收标准
- [ ] 能说出 6 个参数各自的物理意义与测量方法
- [ ] 能解释为什么估计顺序不能乱
- [ ] 能独立算出电流环 Kp/Ki 并说明带宽选择依据
- [ ] 能用频域分析判断稳定性（相位裕度/幅值裕度）
- [ ] 能对比「计算增益」与「Autotuner 增益」的差异并解释

### 常见坑
- 用线性电感给饱和电机算增益（应取额定工作点电感）
- 忘记把 Ki 乘 Ts（模块输入是 Ki·Ts）
- 惯量 J 估错导致转速环振荡

---

## 阶段 6：非线性 LUT 实战（2 周）★ 核心阶段

### 目标
掌握「FEA/实测数据 → 电感表 → 参考电流表 → 控制器」的完整链路，能复现 e11 方案。

### 必读
1. `mathworks/fwc-mtpa-nonlinear-pmsm-lut.md` 全文（尤其「为自定义电机生成查表数据」14 步）
2. `mathworks/lut-based-pmsm-control-reference.md` §参数（LUT 断点向量全集）
3. `mathworks/sq-pmsm-block.md` §建模精度（Tabulated 模式）

### 动手实验
**实验 6.1 数据清洗**
- 取 e11 的 ECE 数据（`results/e11-ece-91x91/`）
- 按 `Lq=λq/iq`、`Ld=(λd−λpm)/id` 反推电感表
- 处理零电流处的除零（邻点插值或极限值）
- 画 Ld(id,iq)、Lq(id,iq) 三维图，检查单调性与平滑性

**实验 6.2 建表**
- 导出 CSV → `seed.Ldfilepath` / `seed.Lqfilepath`
- `mcbGenerateTables(pmsm, inverter, 'jmagindfiles2inddq', seed)`
- `mcbGenerateTables(pmsm, inverter, 'idiqLUTs', seed)`
- 检查生成的 id(T,ω)、iq(T,ω) 表是否覆盖全部工况

**实验 6.3 配置模块**
- 用 `LUT based PMSM Control Reference`，参数输入方式选
  `Non-linear model with Ld, Lq, and FluxPM LUTs`
- 填入 LUT 与断点向量，跑转矩/转速阶跃
- 对比「线性模型」与「非线性模型」的转矩误差（饱和区应明显）

**实验 6.4 纯 Simulink 对照对象**
- 用 Simscape `PMSM` 模块的 `Tabulated Ld, Lq and PM` 模式
- 填同一套表，与 Twin Builder ECE 对象对比同工况响应
- 记录差异，判断是 Park 约定、初始位置还是数据本身的问题

### 验收标准
- [ ] 能独立完成「ECE 数据 → 干净电感表 → id/iq 参考表」全流程
- [ ] 能解释三种非线性输入方式（Ldq LUT / DQ 磁链 LUT / id-iq LUT）的取舍
- [ ] 非线性模型与线性模型的转矩差异能用饱和解释
- [ ] Simulink 对象与 ECE 对象在同工况下误差可解释（< 5%）

### 常见坑
- 电感表在零电流处出现 NaN/Inf
- LUT 断点向量与表维度不匹配
- 忘记 `PMSMLUT.FluxPMTable = pmsm.FluxPM*ones(size(PMSMLUT.LdTable))`
- 两个对象的 Park 变换归一化不一致（2/3 vs √(2/3)）

---

## 阶段 7：部署与验证（1 周）

### 目标
把仿真模型变成硬件上能跑的代码，掌握上板前的校准与排故。

### 必读
1. `mathworks/foc-pmsm-using-quadrature-encoder.md` 全文（14 步部署流程）
2. `mathworks/estimate-pmsm-parameters.md` §部署（ADC 偏移、QEP 校准、保护）
3. `mathworks/field-oriented-current-controller.md` §端口（Debug 信号用法）

### 动手实验
**实验 7.1 仿真→代码**
- 打开 `mcb_pmsm_foc_qep_f28379d`，先仿真通过
- 检查模型配置（求解器、采样时间、目标硬件）
- 生成代码，检查代码大小与执行时间

**实验 7.2 上板校准**
- ADC 偏移校准（`inverter.ADCOffsetCalibEnable`）
- QEP 索引偏移校准（`pmsm.PositionOffset`）
- 开环小电流试转，确认相序与方向

**实验 7.3 闭环运行**
- 低速闭环（10% 基速），观察电流波形
- 逐步升速到基速，再到弱磁区（小步长）
- 用 Debug 端口记录 Idq/Vdq，与仿真对比

**实验 7.4 故障排查演练**
- 故意设错位置偏移 → 观察大电流（理解为什么必须先校准）
- 故意设错极对数 → 观察转速反馈错误
- 记录排故路径：现象 → 可能原因 → 验证方法

### 验收标准
- [ ] 能独立完成「仿真→生成代码→部署→校准→闭环运行」全流程
- [ ] 能解释 ADC 偏移和 QEP 偏移各自影响什么
- [ ] 能说出至少 5 种上板异常的排查顺序
- [ ] 硬件运行波形与仿真趋势一致

### 常见坑
- 位置偏移错导致过流（文档明确警告）
- 弱磁区转速给定跳变导致失稳
- 忘记给 CPU2 加载占位程序（F28379D 双核）
- 串口端口号写错导致 host 模型连不上

---

## 2. 速成版（4 周，适合有基础、赶项目）

| 周 | 内容 | 文档 |
|---|---|---|
| 1 | 数学模型 + 约束曲线 + 标幺 | `mtpacontrolreference`、`pmsm-characteristics`、`per-unit-system` |
| 2 | FOC 双环 + 成品模块 | `field-oriented-control`、`field-oriented-current-controller`、`design-current-controller` |
| 3 | MTPA + 弱磁 + LUT | `field-weakening-control-mtpa-pmsm`、`fwc-mtpa-nonlinear-pmsm-lut`、`lut-based-pmsm-control-reference` |
| 4 | 参数 + 整定 + 部署 | `estimate-pmsm-parameters`、`estimate-control-gains-and-tune`、`foc-pmsm-using-quadrature-encoder` |

速成版跳过：约束曲线手算实验、开环启动实验、纯 Simulink 对照对象、故障演练。

---

## 3. 自测题（每阶段结束后做，答案在对应文档里）

**阶段 1**
1. IPMSM 的转矩由哪两部分组成？各由什么产生？
2. 电压椭圆为什么随转速升高而收缩？
3. 基速的定义里为什么强调「额定电压、额定负载、不弱磁」？

**阶段 2**
4. 为什么 PI 控制器控制直流量比控制交流量效率高？
5. SVPWM 与 SPWM 的 V_base 分别是多少？差多少倍？
6. 标幺制会改变系统的物理响应吗？

**阶段 3**
7. 电流环的带宽为什么必须高于转速环？通常高多少倍？
8. 反 Park 变换的输出是什么？下一步送到哪里？
9. 开环切闭环时，PI 积分器为什么必须复位到开环输出值？

**阶段 4**
10. 写出 IPMSM 的 MTPA 电流公式，并说明 Lq=Ld 时会退化成什么？
11. 三个里程碑转速分别对应哪三条曲线的交点？
12. VCLMT 与 CVCP 的本质区别是什么？

**阶段 5**
13. 参数估计为什么必须按 Rs→Ld→Lq→(Ke,J,B) 的顺序？
14. 用 `mcb.calcFOCGains` 算增益时，Ld/Lq 应该取哪个工作点的值？
15. 相位裕度低于多少就认为系统有振荡风险？

**阶段 6**
16. 为什么非线性电机不能直接用线性 Ld/Lq 做 MTPA？
17. 三种非线性参数输入方式分别需要什么数据？
18. LUT 表的断点向量与表矩阵维度必须满足什么关系？

**阶段 7**
19. ADC 偏移没校准会发生什么？QEP 偏移没校准呢？
20. 上板后电机不转，按什么顺序排查？

---

## 4. 学习产出物（建议边学边攒）

| 产出 | 内容 | 对应阶段 |
|---|---|---|
| 公式手抄本 | dq 方程、转矩、基速、MTPA、弱磁 | 1、4 |
| 约束曲线图集 | 至少 3 台电机 × 4 种 FW 方法 | 1、4 |
| FOC 模型 v1 | 从零搭的双环（SI 版） | 3 |
| FOC 模型 v2 | 改成 PU + 成品模块 | 3 |
| 参数表 | 至少 1 台电机的完整参数与来源 | 5 |
| 增益记录表 | 计算值 / Autotuner 值 / 实测响应 | 5 |
| LUT 数据集 | 电感表 + 参考电流表 + 验证图 | 6 |
| 上板日志 | 校准值、异常现象、排查过程 | 7 |

---

## 5. 延伸方向（学完主线后）

| 方向 | 入口文档/关键词 |
|---|---|
| 无传感器控制 | Sliding Mode Observer / Flux Observer / Extended EMF Observer（`field-oriented-control` 提及） |
| 弱磁的磁链环整定 | FOC Autotuner（弱磁模式）——见 `gain-calculation-and-tuning.md` |
| 单电阻采样 | Phase Current Extractor / PWM Phase Shift for Single Shunt FOC |
| 过调制与电压利用率 | Overmodulation 模块 |
| 死区补偿 | Dead-Time Compensator 模块 |
| 直接转矩控制 DTC | Direct Torque Control (DTC) 示例 |
| 多电机/测功机 | Dual Motor Dyno 示例 |
| HIL 测试 | FOC of PMSM Using HIL Simulation |
| 定点与代码优化 | Fixed-Point Designer + 标幺制 |
| 功能安全 | MISRA C / ISO 26262 工作流（MCB 代码生成） |

---

## 6. 每周节奏建议

| 时段 | 做什么 |
|---|---|
| 周一 | 读 1–2 篇文档，做笔记（只记「为什么」和「公式来源」） |
| 周二–周三 | 动手实验，跑通仿真 |
| 周四 | 做自测题，回文档补漏 |
| 周五 | 整理产出物（图/表/模型），写 200 字小结 |
| 周末 | 自由探索（延伸方向）或补进度 |

> 💡 **一条经验**：每个阶段结束时，用自己的话把该阶段讲给「三个月前的自己」听。
> 讲不通的地方就是没学透的地方——回到对应文档的那一节重读。
