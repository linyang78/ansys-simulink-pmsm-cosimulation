# MathWorks 官方文档存档（中英对照）

> 存档日期：2026-10-21 · 页面版本标注 R2026b
> 用途：官方原文**逐段照录 + 中文对译**，供对照阅读
> 我的整理版笔记另见 `../ipm-foc-mtpa-field-weakening.md`

## 文件清单

### 已有（中英分文件）

| 主题 | 英文 | 中文 |
|---|---|---|
| MTPA Control Reference（模块参考，含全部公式） | `mtpacontrolreference.en.md` | `mtpacontrolreference.zh-CN.md` |
| Field-Weakening Control (with MTPA) of PMSM（示例） | `field-weakening-control-mtpa-pmsm.en.md` | `field-weakening-control-mtpa-pmsm.zh-CN.md` |
| Field-Oriented Control（FOC 原理） | `field-oriented-control.en.md` | `field-oriented-control.zh-CN.md` |

### 本次新增（单文件内中英对照）

| 主题 | 文件 | 价值 |
|---|---|---|
| **PMSM 驱动特性与约束曲线** | `pmsm-characteristics-constraint-curves.md` | ⭐⭐⭐ 电流圆/电压椭圆/MTPV 三段划分，含 `mcb.PMSMCharacteristics` 用法 |
| **非线性 PMSM 的弱磁（查表法）** | `fwc-mtpa-nonlinear-pmsm-lut.md` | ⭐⭐⭐ 与本项目方案最接近：电感查表 → 参考电流表 |
| 增益计算与整定 | `gain-calculation-and-tuning.md` | ⭐⭐ PI 增益计算函数与整定顺序 |
| 开环与闭环控制技术 | `open-loop-and-closed-loop-control.md` | ⭐⭐ V/F 控制、矢量控制、开闭环切换 |
| 标幺制 | `per-unit-system.md` | ⭐⭐ 基础值定义（V_base = Vdc/√3 等） |
| PMSM 模块（Simscape Electrical） | `sq-pmsm-block.md` | ⭐⭐ 电机本体模块，支持 (id,iq) 查表模式 |

### 第二批新增（2026-10-21，中英对照；zh/en 均已下载）

| 主题 | 文件 | 价值 |
|---|---|---|
| **估计控制增益并调节控制参数** | `estimate-control-gains-and-tune.md` | ⭐⭐⭐ Autotuner / 初始化脚本 / `mcb.calcFOCGains` 四种增益路线 + 全部函数表 |
| **使用参数估计模块估计 PMSM 参数** | `estimate-pmsm-parameters.md` | ⭐⭐⭐ Rs→Ld→Lq→(Ke,J,B) 台架整定流程，模型 `mcb_pmsm_param_est_f28379d` |
| **使用 Motor Control Blockset 创建被控对象模型** | `creating-plant-model.md` | ⭐⭐⭐ 搭被控对象六步：电机+逆变器+采样+延迟+集成 |
| **使用正交编码器的 PMSM 磁场定向控制** | `foc-pmsm-using-quadrature-encoder.md` | ⭐⭐⭐ MCB 标杆 FOC 示例（转速外环+dq 电流内环，可上 C2000） |
| **设计磁场定向控制算法** | `design-field-oriented-control-algorithm.md` | ⭐⭐ 搭控制器五步工作流总纲 |
| **设计电流控制器子系统** | `design-current-controller.md` | ⭐⭐ 第 2 步详展：双 PI + Clarke/Park + PWM 生成 + 函数调用调度 |
| **LUT based PMSM Control Reference（模块）** | `lut-based-pmsm-control-reference.md` | ⭐⭐⭐ e11 主方案的对应模块：四种参数输入方式 + LUT 参数全集 |
| **Field-Oriented Current Controller（模块）** | `field-oriented-current-controller.md` | ⭐⭐ 电流内环成品模块：端口/饱和方法/PWM 方式 |

> 模块参考页（`lut-based-...`、`field-oriented-current-controller.md`）中文站无官方翻译，存档以英文
> 原文为主并附整理者翻译；其余各页官方中英文均有，逐段对照。

## 源地址

```
# 已有三篇
https://www.mathworks.com/help/mcb/ref/mtpacontrolreference.html
https://www.mathworks.com/help/mcb/gs/field-weakening-control-mtpa-pmsm.html
https://www.mathworks.com/help/mcb/gs/implement-motor-speed-control-by-using-field-oriented-control-foc.html

# 新增五篇
https://www.mathworks.com/help/mcb/ug/pmsm-characteristics-constraint-curves.html
https://www.mathworks.com/help/mcb/gs/fwc-with-mtpa-of-non-linear-pmsm-using-lut.html
https://www.mathworks.com/help/mcb/gain-calculation-and-tuning.html
https://www.mathworks.com/help/mcb/gs/open-loop-and-closed-loop-control.html
https://www.mathworks.com/help/mcb/gs/per-unit-system.html
https://www.mathworks.com/help/simscape-electrical/ref/pmsm.html

# 第二批八篇（2026-10-21）
https://www.mathworks.com/help/mcb/gs/pmsm-parameter-estimation-using-recommended-hardware.html
https://www.mathworks.com/help/mcb/ug/creating-plant-model.html
https://www.mathworks.com/help/mcb/gs/foc-pmsm-using-quadrature-encoder.html
https://www.mathworks.com/help/mcb/gs/estimate-control-gains-from-motor-parameters.html
https://www.mathworks.com/help/mcb/ug/design-field-oriented-control-algorithm.html
https://www.mathworks.com/help/mcb/ug/design-current-controller.html
https://www.mathworks.com/help/mcb/ref/lutbasedpmsmcontrolreference.html
https://www.mathworks.com/help/mcb/ref/fieldorientedcurrentcontroller.html
```

> **中文站访问说明**：`ww2.mathworks.cn` 常返回 403。
> 把域名换成 `www.mathworks.com` 通常能取到同一篇英文正文；需要中文时用 `?lang=zh_CN` 变体。

## 关于公式

原页面公式是图片 / MathML，网页转文本时会散架。存档时把公式**还原成纯文本**放进代码块，
符号沿用官方写法（`id_mtpa`、`iq_fw`、`λpm`、`ωbase` 等）。

这是**可检索、可复制的等价文本，不是排版复刻**。要权威排版请回源地址。

## 本机配套资源

| 资源 | 位置 |
|---|---|
| 示例模型与脚本（18 个文件） | `help/matlab-examples/field-weakening-mtpa/` |
| 我的整理版学习笔记 | `help/docs/ipm-foc-mtpa-field-weakening.md` |
| e11 的 ECE 数据 | `results/e11-ece-91x91/`（最高精度）、`61x61/`、`20x20/`、`e11-ece/` |

## 与 e11 项目的关联

通用公式见各文件；代入 e11 参数后的实算结果记录在 `docs/design/e11-control-model.md` §3.1.1，
不在此重复。

各文件末尾的「对 e11 的含义 / 落地建议」是为本项目加的批注，**不是官方原文**，已用 💡 或 ⚠️ 标出。
