# Motor-CAD ECE 提取 —— 使用手册

> 适用版本：Motor-CAD 2026 R1 + ansys-motorcad-core 0.8.8 + Python 3.12（conda `pmsm`）
> 手册日期：2026-10-21
> 目的：从 `.mot` 模型导出 Twin Builder 可导入的 ECE 三件套（SML / TXT / MAT）

---

## 一、这套东西是什么

ECE（Equivalent Circuit Extraction，等效电路提取）把 Motor-CAD 的 FEA 结果压缩成一张
**(id, iq, 转子位置) → (磁链, 转矩)** 的查表，由 Twin Builder 读入后生成一个「黑盒电机」组件。

```
e11_User.mot
    │  ① 开环反电势计算 → 对齐角
    │  ② D/Q 电流扫描 FEA → 饱和图 MAT
    │  ③ 展平成查表 → TXT + SML
    ▼
ECE_e11_xx_map.mat  +  ECE_e11_xx_txt_file.txt  +  ECE_e11_xx_sml_file.sml
    │  ④ Twin Builder: Tools → Project Tools → Import Twin Builder Models
    ▼
Twin Builder 工程里的 ECE 组件（三相端 + 机械端）
```

---

## 二、文件清单

| 类别 | 路径 | 说明 |
|---|---|---|
| **主程序** | `scripts/run_ece_export.py` | 命令行入口，读配置 → 跑导出 → 落产物 |
| **核心模块** | `src/motorcad_controller/ece_exporter.py` | 全部逻辑：网格推导、查表构建、TXT/SML 写出 |
| **单测** | `tests/test_ece_exporter.py` | 32 项，覆盖不依赖 Motor-CAD 的纯计算部分 |
| **配置** | `config/cases/e11_ece_config*.json` | 每套网格一份（8×8 / 20×20 / 41×41 / 61×61 / 81×81 / 91×91） |
| **官方原始脚本** | `models/motorcad/ece/MotorCAD_ECE_Export.py` | 随 Motor-CAD 安装的教程脚本（作为格式标准答案保留） |
| **产物** | `results/e11-ece*/` | 三件套按网格分目录 |

> `models/motorcad/ece/` 下的 `MotorCAD_ECE_Export.py` 是**对照用的官方原件**，
> 不是日常执行入口。日常一律用 `scripts/run_ece_export.py`。

---

## 三、快速上手

```powershell
# 解释器固定用 conda pmsm 环境的 python
$PY = 'C:\Env\miniconda3\envs\pmsm\python.exe'

# 1) 先干跑，校验配置与路径（不连 Motor-CAD，秒级）
& $PY scripts/run_ece_export.py --config config/cases/e11_ece_config.json --dry-run

# 2) 正式导出（会连 Motor-CAD、跑 FEA，耗时见下表）
& $PY scripts/run_ece_export.py --config config/cases/e11_ece_config.json
```

**前提**：Motor-CAD 无需预先打开脚本会自动起（`open_new_instance=True`）。
若已有实例，脚本也能接上。

---

## 四、配置文件怎么改

以 `config/cases/e11_ece_config.json` 为例：

```json
{
  "mot_source": "../../models/motorcad/e11_User.mot",
  "base_name": "e11",
  "output_dir": "../../results/e11-ece",
  "shaft_speed": 6000,
  "dc_bus_voltage": 400,
  "machine_temp": 65,
  "id_max": 433,
  "current_step": 108.25
}
```

| 键 | 含义 | e11 取值 | 备注 |
|---|---|---|---|
| `mot_source` | 源 `.mot`（**只读**） | `e11_User.mot` | 脚本先复制到 `<output_dir>/work/` 再操作 |
| `base_name` | 产物名主干 | `e11` | 模型名会成为 `MODELDEF ECE_<base_name>` |
| `output_dir` | 产物目录 | `results/e11-ece` | 相对路径按配置文件所在目录解析 |
| `shaft_speed` | 开环反电势计算转速 | 6000 rpm | 空载运行，不涉及母线电压约束 |
| `dc_bus_voltage` | 母线电压 | 400 V | 影响饱和图中的电压相关量 |
| `machine_temp` | 绕组/磁钢温度 | 65 ℃ | 决定电阻与磁性能 |
| `id_max` | 电流扫描 ±上限 | 433 A | 取**峰值**电流（不是 rms） |
| `current_step` | 扫描步长 | 108.25 A | 见下文「网格怎么选」 |

### ⚠️ 网格必须包含 0 A

Motor-CAD 硬性要求：`Saturation and Loss Map Export requires a point at Id = 0`。

因此 `2×id_max / current_step` 必须是**偶数**，网格点数为奇数：

| 段数 | 点数/轴 | 步长（±433 A） | 负载点数 | 实测耗时 |
|---|---|---|---|---|
| 8 | 9 | 108.25 | 81 | 5.2 min |
| 20 | 21 | 43.30 | 441 | 29.5 min |
| 40 | 41 | 21.65 | 1,681 | 约 112 min |
| 60 | 61 | 14.43 | 3,721 | 243.5 min |
| 90 | 91 | 9.62 | 8,281 | 约 9 h |

脚本在做 FEA 前会先本地校验网格（`_check_grid_contains_zero`），不合格直接报错，
不会白跑几小时才发现。

---

## 五、输出产物

目录结构：

```
results/e11-ece-61x61/
├── ECE_e11_61x61_map.mat          ← 饱和图原始数据（最大）
├── ECE_e11_61x61_txt_file.txt     ← 可读的查表
├── ECE_e11_61x61_sml_file.sml     ← Twin Builder 导入用
└── work/                          ← 中间产物（FEA 结果，不进 git）
```

| 文件 | 内容 | 用途 |
|---|---|---|
| `*_map.mat` | `Id_Peak`/`Iq_Peak`/`Angular_Flux_Linkage_D/Q`/`Angular_Rotor_Position`/`Angular_Electromagnetic_Torque`/`Phase_Advance` 等 | 二次加工的原料；`Ld`/`Lq` 反推就是从这里取 |
| `*_txt_file.txt` | `B_BasicData`（极数、电阻、电感）+ `B_Sweepings`（电流/位置网格）+ `B_OutputMatrix DQ0`（Ψd/Ψq/Ψ0/转矩） | 人工核对、外部工具读表 |
| `*_sml_file.sml` | Twin Builder 模型定义：8 个端口 + Park 变换网络 + pwl 查表 | **导入 Twin Builder 用这个** |

### SML 的 8 个端口

| 端口 | 类型 | 含义 |
|---|---|---|
| `A0` `B0` `C0` | electrical | 三相绕组端（接逆变器桥臂） |
| `X0` `Y0` `Z0` | electrical | 三相中性点端（星点，通常接地） |
| `ROT1` `ROT2` | ROTATIONAL_V | 机械端口（接负载/转速源） |
| `ra0` `la0` | REAL IN | 相电阻、端部电感（可在 TB 里改） |
| `Pos` | REAL OUT ANGLE | 转子机械角（deg） |

---

## 六、导入 Twin Builder

```
AEDT → Tools → Project Tools → Import Twin Builder Models
     → 选 ECE_xxx_sml_file.sml → Open
```

组件出现在 `Component Libraries / Project Components` 下。

导入后用 `Edit Symbol → Edit Pin Locations` 排布引脚：
`A0/B0/C0/ROT2` 放左，`X0/Y0/Z0/ROT1` 放右。

---

## 七、故障处置

| 现象 | 原因 | 处置 |
|---|---|---|
| `Cannot perform Lab calculation, Lab is already running` | 饱和图是**异步启动**，这是「已启动」回执 | 脚本已自动处理（不视为失败，转轮询完成标志） |
| `requires a point at Id = 0` | 网格没落在 0 A | 改 `current_step` 使段数为偶数；脚本会提前拦下 |
| `Mesh17: IntRadius and ExtRadius must be defined if air_gap is not meshed` | 气隙未划分网格 | `AnsysAirgapMesh` 必须为 1；脚本已自动检查并修正 |
| 计算卡住不动 | Motor-CAD 实例状态异常 | 结束 Motor-CAD 进程后重跑；脚本每次自起新实例 |
| SML 导入报 action failed | pwl 表数据量与声明不符 | 已修复（见下节「历史缺陷」） |

---

## 八、历史缺陷（已修复，留作排查参考）

| 缺陷 | 症状 | 根因 | 修复 |
|---|---|---|---|
| 回绕模数用样本数 | 查表整体错位一格 | 121 个样本 / 120 个周期步，模数应取周期 | 改用 `grid.points_per_cycle` |
| pwl 表写入整列 | SML 体积大 81 倍（8×8：11.7 MB vs 官方 170 KB），导入报 action failed | 每个电流对写了全部位置点，应为该对的 41 个切片 | 按 `pair*mp` 切片 |
| 输出列次序错 | 查表语义错 | 官方第 3、4 列是 Ψ0（恒 0）与转矩 | 已对齐 |
| 反电势分辨率停在 30 点 | 反电势结果比饱和图粗 | 官方脚本未回写 | 改为两轮：先取对齐角，再按网格点数重跑 |

**验收判据**：与官方 `MotorCAD_ECE_Export.py` 的产物**逐字符相同**（归一化模型名后）。
改动格式相关代码后，务必做一次这个比对。

---

## 九、产物规格参考

| 网格 | 查表行数 | SML 体积 | MAT 体积 | 建议用途 |
|---|---|---|---|---|
| 8×8 | 3,321 | 170 KB | 781 KB | 跑通链路、快速验证 |
| 20×20 | 18,081 | 907 KB | 4.1 MB | MTPA 主表 |
| 61×61 | 157,604 | 7.7 MB | 36 MB | 弱磁 / MTPV 高精度表 |
| 91×91 | 约 35 万 | 约 17 MB | 约 80 MB | 最终精度（耗时约 9 h） |

> 体积不再是约束——修复后每负载点约 0.7 KB，即使 91×91 也只有十几 MB。

---

## 十、不做什么

- **不改源 `.mot`**：全程只在 `work/` 副本上操作
- **不做 Maxwell 导出**：那是 `export_to_ansys_electronics_desktop()`，另一条路径
- **不解析 SML 语义**：只按官方格式生成，正确性靠与官方产物比对
- **不做弱磁控制设计**：ECE 只提供电机本体数据，控制器在 Simulink 侧
