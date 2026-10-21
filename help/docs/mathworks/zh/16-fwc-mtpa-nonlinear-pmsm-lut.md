# 非线性 PMSM 的弱磁控制（含 MTPA）——基于查表

> **MathWorks 官方文档存档（中文）**
> 来源：`https://ww2.mathworks.cn/help/mcb/gs/fwc-with-mtpa-of-non-linear-pmsm-using-lut.html`（正文取自英文站）
> 存档：2026-10-21 · R2026b · 英文版：`en/16-fwc-mtpa-nonlinear-pmsm-lut.md`
> 说明：官方正文逐段整理。

---

## 概述

此示例对非线性 PMSM 与控制器使用查表（LUT）来实现弱磁控制（含 MTPA）。
可用它在仿真中复现并运行基于有限元分析（FEA）的非线性高保真 PMSM。

该示例帮助电机设计工程师在真实电机控制应用中仿真高性能电机；
控制系统工程师也可用它基于给定的电机参数数据设计控制算法，
在转速与转矩跟踪控制上达到高精度并满足效率要求，尤其针对高性能电机。

---

## 为什么用查表

传统上要获得最优参考电流数据，需要实测电机与台架硬件。
但用实物电机和硬件同时做电机设计与控制算法设计，成本高、耗时长、有安全问题，
且机器与逆变器偶发故障——实际上不可行。

本示例用查表驱动的仿真模型有效解决该问题。**它使用一个包含 Ld、Lq 相对 id、iq 变化数据的查表。**

示例采用「基于 LUT 的 PMSM Control Reference」模块，利用 PMSM 的非线性电感与永磁磁链数据，
通过迭代解析方法设计并实现弱磁转矩控制的 id(转矩, 转速) 与 iq(转矩, 转速) 查表。

默认情况下，示例使用基于集中参数值生成的表格化电机特性数据。
作为替代方案，你可以配置该模块生成自己的参考电流查表并在同一示例中使用。

由于对非线性高性能电机求解底层电机方程计算量很大，示例依赖「解这些**未近似**的方程」所生成的查表。
这样在控制器硬件上运行控制算法时精度很高（因为查表数据复现了真实的非线性电机特性）。

采用这一方法，可以减轻「由控制器硬件求解非线性 PMSM 近似方程」所带来的复杂性。

该示例帮助你构建弱磁（含 MTPA）控制算法，以补偿因定子铁芯磁饱和导致的非线性所带来的转矩损失。

关于这些运行区域的细节，请参阅《Field-Weakening Control (with MTPA) of PMSM》与
《PMSM Drive Characteristics and Constraint Curves》。

---

## 模型

示例包含 `mcb_pmsm_nonlin_fwc` 模型，**仅用于仿真**。

**必需的 MathWorks 产品：** Motor Control Blockset™, Simscape™ Electrical™

---

## 查表数据文件

默认使用数据文件 `IPMSM_template_data.mat`，由模型初始化脚本 `mcb_pmsm_nonlin_fwc_data.m` 加载读取。

模型中用到这些查表的模块：

- **LUT based PMSM Control Reference**：使用由电感查表导出的参考电流查表
- **PMSM Feed Forward Control**：使用电感查表
- **Motor Model** 有两种可选：
  - **Non-linear PMSM with 2D LUTs**：用 Simscape PMSM 模块读取 .mat 里的 (id, iq) 二维数据
  - **FEM Parameterized PMSM 2D LUTs**：用 FEM-Parameterized PMSM 模块

---

## 仿真步骤

1. 打开 `mcb_pmsm_nonlin_fwc.slx`
2. 用 **Motor Plant Model** 单选按钮选择电机模型：
   a. Non-linear PMSM with 2D LUTs
   b. FEM Parameterized PMSM with 2D LUTs
3. 点 **仿真** 选项卡的 **Run**
4. 用 **Speed Reference (RPM)** 与 **Torque Reference (Nm)** 旋钮设定参考转速与参考转矩
5. 点 **Data Inspector** 查看分析结果

注意：可用模型里的滑条改变电池工作电压来模拟不同工况。

---

## 为自定义电机生成查表数据

以下步骤说明如何获得电感查表数据（手工生成或从 JMAG 下载），并用于相同或类似的示例模型。

1. **获取 .rtt 文件与 RT-Viewer 工具**
   a. 从 JMAG-RT Model Library 下载你电机的查表数据（.rtt 文件），其中包含 Ld、Lq 映射。
      注意：下载与使用该文件需要 Type-2（免费）许可。
   b. 获取 RT-Viewer 工具（JMAG-RT Viewer）。

2. **用 RT Viewer 打开 .rtt**，把 Ld、Lq 表导出成 id、iq 同一网格格式，例如 `JMAG_Ld.csv`、`JMAG_Lq.csv`。
   a. 菜单 **Table Value > Inductance > Id-Iq-Ld**
   b. **Map Window > File > CSV Export**
   c. 填入 id、iq 网格信息与文件名
   注意：若已有手工生成的查表数据，跳过 1、2 步。

3. **在模型初始化脚本中**创建模板结构体：
   ```matlab
   pmsm = mcb_SetPMSMMotorParameters('Teknic2310P');
   inverter = mcb_SetInverterParameters("BoostXL-DRV8305");
   pmsm.B = pmsm.B*100;   % 提高粘性阻尼系数，因为该电机比 Teknic2310P 更大
   ```

4. **更新以下字段：**
   `pmsm.p`（极对数）、`pmsm.Rs`（定子/绕组电阻）、`pmsm.Ld`、`pmsm.Lq`、`pmsm.J`（惯量）、
   `pmsm.FluxPM`（永磁磁链）、`pmsm.I_rated`（额定电流）、`inverter.V_dc`（额定电压）。

5. **计算额定转矩：**
   ```matlab
   pmsm.T_rated = mcbPMSMRatedTorque(pmsm);
   ```

6. **创建 seed 结构体**，写入 CSV 路径：
   ```matlab
   seed.Ldfilepath = 'JMAG_Ld.csv';
   seed.Lqfilepath = 'JMAG_Lq.csv';
   ```

7. **创建查表：**
   ```matlab
   PMSMLUT = mcbGenerateTables(pmsm, inverter, 'jmagindfiles2inddq', seed);
   ```
   该命令把 CSV 转成规则矩阵，空位用外插填充。
   由于永磁磁链（FluxPM）也需要同样的查表格式：
   ```matlab
   PMSMLUT.FluxPMTable = pmsm.FluxPM*ones(size(PMSMLUT.LdTable));
   ```

8. **配置以下模块**使用非线性查表：
   - **LUT based PMSM Control Reference** → 电机参数输入方法 = *Non-linear model with id and iq LUTs*
   - **PMSM Feed Forward Control** → *Non-linear model with Ld, Lq and FluxPM LUTs*
   - **PMSM Torque Estimator** → *Non-linear model with Ld, Lq and FluxPM LUTs*

9. 用 **FEM-Parameterized PMSM** 模块搭被控对象。

10. FEM-Parameterized PMSM 模块：**Modelling option** = *2-D partial derivative data | No thermal port*

11. **Electrical** 栏：**Parameterization** = *Assume sinusoidal back emf - tabulate with d- and q- axis currents*

12. **由电感查表生成 id、iq 参考电流表：**
    ```matlab
    PMSMLUT = mcbGenerateTables(pmsm, inverter, 'idiqLUTs', seed);
    ```
    关于 seed 变量结构：`help mcbGenerateTables`。
    也可以用 Model-Based Calibration Toolbox™ 标定并生成 id/iq 查表。

13. **按参数输入方法把各表填入 PMSM 查表字段：**
    ```matlab
    PMSMLUT.idVec
    PMSMLUT.iqVec
    PMSMLUT.LdTable
    PMSMLUT.LqTable
    PMSMLUT.FluxPMTable
    % 或者
    PMSMLUT.trefVec
    PMSMLUT.wrpmVec
    PMSMLUT.idTable
    PMSMLUT.iqTable
    ```

14. 把其余电机参数填到相应位置。

15. **PMSM 被控对象模型：**
    - 定子零序电感保持默认值
    - 在机械参数部分更新 `pmsm.B` 与 `pmsm.J`
    - 转子转速与位置初值设为 0

---

## 相关示例

- PMSM Drive Characteristics and Constraint Curves
- Field-Weakening Control (with MTPA) of PMSM

## 另请参阅

- LUT based PMSM Control Reference
- Designing a Torque Controller for a PMSM through Simulation on a Virtual Dynamometer

---

## 对 e11 的落地建议

> 以下为项目批注，非官方原文。

这一段流程对本项目有直接价值：

| 官方步骤 | e11 对应做法 |
|---|---|
| 第 1–2 步：拿 Ld(id,iq)、Lq(id,iq) 表 | 用 `results/e11-ece-91x91/ECE_e11_91x91_map.mat` 里的 `Flux_Linkage_D/Q` 反推 |
| 第 3–5 步：填电机结构体 | `p=4`、`Rs=0.01338`、`FluxPM=0.075883`、`I_rated` 待定、`V_dc=400` |
| 第 6–7 步：CSV 转查表矩阵 | `mcbGenerateTables(pmsm, inverter, 'idiqLUTs', seed)` |
| 第 8 步：模块切非线性模式 | LUT based PMSM Control Reference 选 *Non-linear model with id and iq LUTs* |

⚠️ **必须先修电感表**：e11 的 MAT 里 `Ld`/`Lq` 字段在零电流处是除零产物（读到 `-7.4e13`），
且量纲与 `varUnits` 标称不符。要按定义反推：
`Lq = λq/iq`（Id=0 时）、`Ld = (λd − λpm)/id`（Iq=0 时），再导出 CSV。
