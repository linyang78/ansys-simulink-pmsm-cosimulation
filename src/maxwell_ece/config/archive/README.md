# 归档配置

这里的配置是**历史运行记录**，`source_project` 与 `output_dir` 指向已不存在的旧位置
（旧仓库根 `C:\Users\xlin\Desktop\simulink\`、旧版本目录 `versions/v0.3/`）。

**不要直接运行它们**——路径会解析失败，`source_hash` 也已与当前模型不符。

用途仅限查阅当时的扫描参数（电流点、转角区间、`ph_ang_intervals` 等）。

## 生成当前可用的配置

在 `src/maxwell_ece/` 下执行：

```powershell
$py  = 'C:\Env\miniconda3\envs\pmsm\python.exe'
$mot = '..\..\models\aedt\E11_FULL\e11_PMSM_IPM.aedt'
& $py scripts\maxwell_ece.py draft $mot --design PMSM_Healthy --setup Setup1 --write config\draft.json
```

`draft` 会重新计算 `source_hash` 并写入当前物理路径。
