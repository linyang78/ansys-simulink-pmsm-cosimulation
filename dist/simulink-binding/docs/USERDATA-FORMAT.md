# UserData 字段格式

Simulink 侧 `AnsoftSFunction` 块的 `UserData` 参数承载了与 Twin Builder 的绑定关系。
本工具不通过界面逐个点 Link 建立映射，而是直接构造这个字符串并写回块。

格式已验证：构造出的值与你手工在对话框里操作后由官方组件写出的值**逐字节一致**。

## 格式

逗号分隔，共 8 + N 个字段：

```
DataVer:2,<aedt路径>,<project>,<design>,<analysis>,<实例名>,<输出数>,<输入数>,<输出信号名...>,<输入信号名...>,<索引...>
```

| # | 字段 | 示例 | 说明 |
|---|---|---|---|
| 0 | `DataVer:2` | `DataVer:2` | 版本前缀，固定 |
| 1 | `.aedt` 路径 | `E:\...\RotorySimulink_thincoder.aedt` | **绝对路径** |
| 2 | project | `RotorySimulink_thincoder` | `.aedt` 文件名去扩展名 |
| 3 | design | `MatlabConnect` | Twin Builder 内的设计名 |
| 4 | analysis | `TR` | 分析名（Transient） |
| 5 | 实例名 | `MDL1` | `.aedt` 内元件实例名，**必须与原文一致** |
| 6 | 输出数 | `6` | 「输出」= Twin Builder 输出给 Simulink 的信号数 |
| 7 | 输入数 | `4` | 「输入」= Simulink 送入 Twin Builder 的信号数 |
| 8.. | 输出信号名 | `iA,iB,iC,wm,THM,Te` | 共「输出数」个 |
| .. | 输入信号名 | `uA,uB,uC,TL` | 共「输入数」个 |
| 末尾 | 索引 | `0,1,2,3,4,5,0,1,2,3` | 共「输出数 + 输入数」个 |

## 完整示例

```
DataVer:2,E:\Vscode\thincoder-pmsm\models\manual\RotorySimulink_thincoder.aedt,RotorySimulink_thincoder,MatlabConnect,TR,MDL1,6,4,iA,iB,iC,wm,THM,Te,uA,uB,uC,TL,0,1,2,3,4,5,0,1,2,3
```

拆解：

```
DataVer:2
E:\...\RotorySimulink_thincoder.aedt
RotorySimulink_thincoder          ← project
MatlabConnect                     ← design
TR                                ← analysis
MDL1                              ← instance
6                                 ← 输出数
4                                 ← 输入数
iA,iB,iC,wm,THM,Te                ← 6 个输出信号名
uA,uB,uC,TL                       ← 4 个输入信号名
0,1,2,3,4,5,0,1,2,3               ← 10 个索引
```

## 索引规则

```
索引 = range(输出数) + range(输入数)
```

示例：

| 输出数 | 输入数 | 索引 |
|---|---|---|
| 6 | 4 | `0,1,2,3,4,5,0,1,2,3` |
| 3 | 3 | `0,1,2,0,1,2` |
| 1 | 2 | `0,0,1` |

即：输出信号依次映射到 Simulink 块的 `Node[0..输出数-1]`，输入信号依次映射到 `Node[0..输入数-1]`。
两组编号**各自从 0 开始**。

## 关键约束

### 不能从 Simulink 块的 `Ports` 属性反推

`Ports` 是 Simulink 侧的方向，与 `.aedt` 的 `direction` 语义相反：

| | Simulink 侧 | Twin Builder 侧 |
|---|---|---|
| `Ports[0]` = 4 | 4 个输入端口 | 对应「输入信号」4 个（如 `uA,uB,uC,TL`） |
| `Ports[1]` = 6 | 6 个输出端口 | 对应「输出信号」6 个（如 `iA,iB,iC,wm,THM,Te`） |

若误用 `range(Ports[0]) + range(Ports[1])` 会得到 `0,1,2,3,0,1,2,3,4,5`，**方向相反，绑定会错**。

正确来源是 `.aedt` 里每个端口的 `SimulinkDirection`：
- `SimulinkDirection=0` → 输出信号（Twin Builder 送给 Simulink）
- `SimulinkDirection=1` → 输入信号（Simulink 送入 Twin Builder）

### 不能从字符串位置反推端口数

字段位置 `[6]`、`[7]` 是本次实测得出的，但换一个模型未必稳定。
可靠做法是从 `.aedt` 的 `SimulinkDirection` 计数得来，或者从块的 `Ports` 按上表换算。

### 名字段顺序不能改

正确顺序是**输出信号名在前、输入信号名在后**，与计数字段 `6,4` 严格对齐：

```
6,4, iA,iB,iC,wm,THM,Te, uA,uB,uC,TL
↑ ↑  └──── 正好 6 个 ────┘└── 4 个 ──┘
```

若写成 `6,4,uA,uB,uC,TL,iA,iB,iC,wm,THM,Te`，计数 `6` 后紧跟的 6 个名字会混两个方向，**绑定错位**。
此约定由你手工操作后 GUI 写出的真值确认。

## 核验方法

写入后读回，三条判据全部满足才算成功：

1. 以 `DataVer:2,` 开头
2. 包含 `.aedt` 绝对路径、design 名、实例名三个子串
3. 末尾索引序列不是全 `-1`，且等于期望值

**`Parameters` 参数不作判据**。实测点 OK 后读回是空串 `''`，
而用户已绑定成功的旧模型里是 `'-1'`，取值不稳定，用它判会误判失败。

**全局比对**：本工具最终判据是「构造串 == 读回串」逐字节相等，不解析任何字段位置。
