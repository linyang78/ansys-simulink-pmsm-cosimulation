# AEDT MCP 使用说明(本机适配版)

> 来源:[CAE-Agent-Hub / MCP / Ansys / AEDT MCP](https://github.com/Cai-aa/CAE-Agent-Hub/tree/main/MCP/Ansys/AEDT%20MCP)(GitHub,2026-08-04 下载)
> 本机位置:`F:\project\AEDT-MCP`(独立目录,不进本项目 git)
> 用途:让 MCP 客户端(Codex、Claude 等)通过 PyAEDT 控制 **Ansys Electronics Desktop 2026 R1**

---

## 1. 是什么 / 架构

```
MCP 客户端(Codex/Claude Desktop/…)
   │  stdio JSON-RPC
   ▼
mcp_server.py (FastMCP stdio server)      ← 常驻,由 MCP 客户端拉起
   │  外部进程(worker)
   ▼
PyAEDT broker(pyaedt_worker)              ← 每个目标(AEDT 实例)一个 broker,复用连接
   │  gRPC
   ▼
AEDT 2026 R1(你的 AnsysEM 实例,含 Maxwell/Twin Builder 等)

关键设计:
- AEDT 内部不运行任何 MCP/脚本/后台线程 —— 干净,无残留
- 显式目标:没有隐式会话,每个工具调用必须传 `pid` 或 `port` 之一
- broker 生命周期:连接复用于多次命令;`release_connection`/MCP 退出才释放;
  关闭 AEDT 窗口会触发 QuitApplication() 并结束 broker;超时只杀 broker,不杀 AEDT
```

## 2. 本机安装

> ⚠️ **版本冲突**:项目依赖锁定 `pyaedt==1.1.0`(面向 AEDT 2026 R1)。
> 本机主环境(`pyaedt` conda env)是 **PyAEDT 1.2.0**,`pip install -e .` 会强制降级,
> **不要**装进主环境。按官方建议建独立环境:

```powershell
# 方式 A:conda 独立环境(本机推荐,与主环境隔离)
conda create -n aedt-mcp python=3.11 -y
conda activate aedt-mcp
cd F:\project\AEDT-MCP
pip install -U pip
pip install -e .

# 方式 B:官方 README 的 venv 方案
cd F:\project\AEDT-MCP
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e .
```

依赖:`mcp>=1.0`、`pyaedt==1.1.0`、`psutil>=5.9,<8`。

## 3. MCP 配置(本机版 mcp_config.json)

把 `examples/mcp_config.example.json` 复制为 `mcp_config.json`,替换 `<repo>` 与本机路径:

```json
{
  "mcpServers": {
    "ansys-aedt": {
      "command": "F:\\project\\AEDT-MCP\\.venv\\Scripts\\python.exe",
      "args": ["F:\\project\\AEDT-MCP\\mcp_server.py"],
      "cwd": "F:\\project\\AEDT-MCP",
      "env": {
        "AEDT_VERSION": "2026.1",
        "AEDT_INSTALL_DIR": "F:\\ANSYS Inc\\v261\\AnsysEM",
        "AEDT_WORKER_TIMEOUT": "60",
        "AEDT_LAUNCH_TIMEOUT": "120",
        "AEDT_LOG_DIR": "%TEMP%\\aedt-mcp"
      }
    }
  }
}
```

- `AEDT_INSTALL_DIR` 必须指向**包含 `ansysedt.exe` 的目录**(本机 `F:\ANSYS Inc\v261\AnsysEM`)
- 客户端接入:Codex/Claude Desktop 等工具按各自方式引入此 mcpServers 配置

## 4. 工具清单

| 工具 | 作用 | 目标参数 |
| --- | --- | --- |
| `list_aedt_sessions` | 发现所有 AEDT 进程 PID 与监听端口(只读,不连接) | 无 |
| `launch_aedt` | 以显式 gRPC 端口启动**可见** AEDT 2026 R1 | 无(返回 port) |
| `check_aedt_connection` | 探测指定目标,首次使用时创建 broker | pid 或 port |
| `release_connection` | 停止并释放该目标的 broker(不关 AEDT/工程) | pid 或 port |
| `get_project_info` | 读取工程与活动设计元数据 | pid 或 port |
| `close_projects` | 关闭显式指定的工程(可选先保存,不删文件) | pid 或 port |
| `create_hfss_design` | 创建或激活指定 HFSS design | pid 或 port |
| `save_project` | 保存活动工程(可另存) | pid 或 port |
| `start_analysis` | 启动指定 HFSS setup(默认非阻塞) | pid 或 port |
| `get_analysis_status` | 查询求解状态与 setup 列表 | pid 或 port |
| `build_wr90_waveguide` | 完整建算例:WR-90 TE10 直波导(真空通道 22.86×10.16×50mm、PEC 壁、双波端口、10GHz 自适应、8-12GHz 81 点扫频) | pid 或 port |

资源:`aedt://status`、`aedt://agent-instructions`(不会隐式连接 AEDT)

## 5. 使用流程

```
1. 启动/发现 AEDT:
   - 已有 AEDT 实例 → list_aedt_sessions 拿 PID
   - 没有 → launch_aedt 启动并拿 port
2. check_aedt_connection(pid=X 或 port=Y)   # 建 broker,真实探测
3. 任意工具调用,每个都传同一个 pid 或 port
4. 用完 release_connection                   # 释放 broker,不关 AEDT
```

**注意**:PID 与 port 是同一 broker 的别名,探测成功后两个标识都指向同一会话。

## 6. 验证(可选)

```powershell
cd F:\project\AEDT-MCP
.\.venv\Scripts\python.exe -m unittest discover -s tests -v      # 单元测试
.\scripts\run_live_acceptance.ps1 -Mode both                     # 实机验收(需要真实 AEDT + 许可)
```

实机验收覆盖:显式 PID/port 定位、同一 broker 连续命令、一次性 HFSS 工程保存、broker 连接中正常关闭 AEDT;出现 "being used by another application, script or extension wizard" 弹窗即失败。

## 7. 注意事项 / 坑

1. **PyAEDT 版本**:锁定 1.1.0(官方面向 2026 R1)。本机 pyaedt 1.2.0 实测也能驱动 2026.1,但**不要改 pyproject 混用**——独立环境各用各的。
2. **显式目标**:工具不带 pid/port 会失败;服务器不会自动选窗口。
3. **gRPC 会话特性**:2026 R1 的 gRPC 监听随 PyAEDT 客户端结束而消失,所以 broker 必须常驻复用连接——这是本架构的核心原因。
4. **关窗行为**:手动关闭 AEDT 主窗口 = 明确退出请求,broker 会调 QuitApplication() 并退出;不要用"关窗口"来临时隐藏。
5. **超时**:broker 超时只杀 broker,不杀 AEDT;启动超时/工作超时分别由 `AEDT_LAUNCH_TIMEOUT`/`AEDT_WORKER_TIMEOUT` 控制。
6. **许可**:与我们的 M0 门禁共用 PLE 许可(1055@localhost),串行使用避免并发冲突。
7. **本机主项目(仿真_workflow)不走 MCP**:项目用 pyaedt 1.2.0 直接驱动(M2/M3),MCP 面向 AI 代理交互;两者可以同时存在,但避免同时对同一 AEDT 实例做写操作。

## 8. 与本项目的整合建议

- **现在**:MCP 工具仅覆盖 HFSS(create_hfss_design/start_analysis/WR-90),与我们的 Maxwell 2D PMSM 流程无直接交集——先作为独立能力备用;
- **将来(可选)**:若需让 AI 代理直接操作 Maxwell/Twin Builder 设计,可仿照 `pyaedt_backend.py`/`pyaedt_worker.py` 模式扩展 worker 命令(项目内已有 PyAEDT 1.2.0 经验与 API 验证,扩展成本低);
- **版本红线**:MCP 环境 pyaedt 1.1.0 与主环境 1.2.0 隔离,升级任一侧前跑各自回归(check_env.py / AEDT-MCP tests)。
