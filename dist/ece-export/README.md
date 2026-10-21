# ece-export — Motor-CAD ECE 等效电路提取

自包含工具包。从 Motor-CAD 的 `.mot` 模型导出 Twin Builder 可导入的 **ECE 三件套**（SML / TXT / MAT），
并可进一步反推电机参数、计算控制参数。

**这个包不依赖原项目**，拷走即可用（需要 Motor-CAD + conda 环境）。

## 它做什么

```
e11_User.mot
    │  ① 开环反电势计算 → 对齐角
    │  ② D/Q 电流扫描 FEA → 饱和图
    │  ③ 展平成查表 → TXT + SML
    ▼
ECE_xxx_map.mat + ECE_xxx_txt_file.txt + ECE_xxx_sml_file.sml
    │  ④ Twin Builder 导入
    ▼
Twin Builder 里的 ECE 组件（三相端 + 机械端）
```

## 调用契约

### 导出 ECE

```powershell
python scripts/run_ece_export.py --config <配置.json>
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `--config` | 是 | 配置 JSON 路径。相对路径按**当前工作目录**解析，配置里的路径按**配置文件所在目录**解析 |
| `--dry-run` | 否 | 只校验配置与路径，不连 Motor-CAD、不计算。**建议先跑一次** |

### 计算控制参数

```powershell
python scripts/calc_control_params.py --mat <ECE_map.mat> [--json-out out.json]
```

| 参数 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `--mat` | 是 | — | ECE 饱和图 MAT |
| `--json-out` | 否 | — | 结果写 JSON |
| `--pwm-hz` | 否 | 20000 | PWM 开关频率 |
| `--current-bw` | 否 | 1000 | 电流环带宽 Hz |
| `--speed-bw` | 否 | 30 | 速度环带宽 Hz |

输出：λpm、Ld/Lq（额定点与饱和端）、凸极率、MTPA 工作点、基速、各转速可达转矩、PI 增益。

### 退出码（`run_ece_export.py`）

| 码 | 含义 | agent 应如何处理 |
|---|---|---|
| 0 | 导出完成，三件套已落盘 | 读 `<output_dir>/` 下的 SML |
| 1 | 导出失败（Motor-CAD 报错 / 计算未完成） | 看 stdout 的 `[导出失败]` 行；区分环境问题与配置问题后**可重试一次** |
| 2 | 配置不可用（文件缺失 / JSON 非法 / 缺键 / `.mot` 不存在） | **不要重试**，是输入问题 |
| 3 | Motor-CAD 连接失败 | 检查 Motor-CAD 是否安装/可启动 |

### 输出格式

stdout 为人类可读中文：

```
配置：<配置路径>
  源模型  <mot 路径>
  工作副本 <work 目录>
  产物目录 <输出目录>
  工况    6000 rpm / 400 V / 65 ℃
  电流网格 ±433 A，步长 108.25 A（约 9 点/轴）
已连接 Motor-CAD（open_new_instance=True）
已复制工作副本（原文件不动）

导出完成，用时 5.2 min
  网格     对齐角 90.000° | 电角步长 3.000° | 每周期 120 点 | 机械步长 0.7500° | 查表 41 点
  极对数   4（8 极）
  每相电阻 1.337736e-02 Ω
  端部电感 6.026926e-06 H
  查表行数 3321
  MAT      <路径>
  TXT      <路径>
  SML      <路径>
```

## 配置说明

见 `config/ece_config.example.json`：

| 键 | 含义 | 备注 |
|---|---|---|
| `mot_source` | 源 `.mot` | **只读**，脚本先复制到 `<output_dir>/work/` |
| `base_name` | 产物名主干 | 模型名成为 `MODELDEF ECE_<base_name>` |
| `output_dir` | 产物目录 | 不存在则创建 |
| `shaft_speed` | 反电势计算转速 | rpm |
| `dc_bus_voltage` | 母线电压 | V |
| `machine_temp` | 绕组/磁钢温度 | ℃ |
| `id_max` | 电流扫描 ±上限 | **峰值** A |
| `current_step` | 扫描步长 | A，见下 |

### ⚠️ 网格必须包含 0 A

Motor-CAD 硬性要求 `Saturation and Loss Map Export requires a point at Id = 0`。

故 `2 × id_max / current_step` 必须是**偶数**（点数 = 段数 + 1 = 奇数）：

| 段数 | 点数/轴 | 步长（±433 A） | 负载点 | 耗时（实测） |
|---|---|---|---|---|
| 8 | 9 | 108.25 | 81 | 5.2 min |
| 20 | 21 | 43.30 | 441 | 29.5 min |
| 60 | 61 | 14.43 | 3,721 | 243.5 min |
| 90 | 91 | 9.62 | 8,281 | 约 9 h |

脚本会在跑 FEA 前本地校验，不合格直接报错（不会白跑几小时）。

## 产物

```
<output_dir>/
├── ECE_<base>_map.mat          ← 饱和图原始数据（可二次加工）
├── ECE_<base>_txt_file.txt     ← 可读查表（Ψd/Ψq/Ψ0/转矩）
├── ECE_<base>_sml_file.sml     ← **导入 Twin Builder 用这个**
└── work/                       ← 中间产物（FEA 结果，可删）
```

### SML 的 8 个端口

| 端口 | 类型 | 含义 |
|---|---|---|
| `A0` `B0` `C0` | electrical | 三相绕组端（接逆变器桥臂） |
| `X0` `Y0` `Z0` | electrical | 三相中性点端（星点，通常接地） |
| `ROT1` `ROT2` | ROTATIONAL_V | 机械端口（接负载/转速源） |
| `ra0` `la0` | REAL IN | 相电阻、端部电感（TB 里可改） |
| `Pos` | REAL OUT ANGLE | 转子机械角（deg） |

## 导入 Twin Builder

```
AEDT → Tools → Project Tools → Import Twin Builder Models → 选 SML → Open
```

组件出现在 `Component Libraries / Project Components` 下。
之后用 `Edit Symbol → Edit Pin Locations` 排布引脚。

## 故障速查

| 现象 | 原因 | 处置 |
|---|---|---|
| `Lab is already running` | 饱和图是**异步启动**，这是启动回执 | 脚本已自动处理，不是错误 |
| `requires a point at Id = 0` | 网格没落在 0 A | 改 `current_step` 使段数为偶数 |
| `air_gap is not meshed` | 气隙未划网格 | `AnsysAirgapMesh` 必须为 1（脚本已自动修正） |
| 计算卡住 | Motor-CAD 实例状态异常 | 结束 Motor-CAD 进程重跑 |
| SML 导入报 action failed | pwl 表数据量与声明不符 | 见 `docs/ece-export-manual.md` 第八节 |

## 环境要求

| 依赖 | 版本 |
|---|---|
| Python | 3.10+（含 `numpy`、`scipy`） |
| conda 环境 | `pmsm`（示例路径 `C:\Env\miniconda3\envs\pmsm\python.exe`） |
| ansys-motorcad-core | 0.8.8 |
| Motor-CAD | 2026 R1 |

## 目录结构

```
ece-export/
├── README.md                       ← 本文件
├── scripts/
│   ├── run_ece_export.py           ← ECE 导出入口
│   └── calc_control_params.py      ← 控制参数计算
├── src/motorcad_controller/
│   ├── __init__.py
│   └── ece_exporter.py             ← 核心逻辑
├── config/
│   └── ece_config.example.json     ← 配置示例
├── tests/
│   └── test_ece_exporter.py        ← 21 项单测（纯计算，不需 Motor-CAD）
└── docs/
    └── ece-export-manual.md        ← 完整使用手册
```

## 自检

```powershell
# 单测（不需要 Motor-CAD，秒级）
python -m pytest tests/ -q

# 配置校验（不需要 Motor-CAD）
python scripts/run_ece_export.py --config config/ece_config.example.json --dry-run
```

## 不做什么

- **不改源 `.mot`**：只在 `work/` 副本上操作
- **不做 Maxwell 导出**：那是另一条路径
- **不解析 SML 语义**：只按官方格式生成，正确性靠与官方脚本产物比对
