# China ISP Probe

部署在中国电信、联通、移动网络中的 VPS/主机上，用于真实测试 Cloudflare IP。

启动：

python3 probe/server.py

环境变量：PROBE_NAME=ctcc/cuсc/cmcc、PROBE_PORT=8787、PROBE_TIMEOUT_MS=2500、PROBE_MAX_BATCH=128。

检查：curl http://127.0.0.1:8787/health

`/scan` 只接受 Cloudflare IPv4 网段，并测试 TCP/443 + TLS SNI speed.cloudflare.com，避免探针成为任意目标扫描器。

接入 GitHub Actions：在仓库 Settings → Secrets and variables → Actions → Variables 中创建 `PROBES_JSON`，例如：

{"ctcc":"https://ctcc.example.com","cucc":"https://cucc.example.com","cmcc":"https://cmcc.example.com"}

没有探针时 ctcc/cucc/cmcc 保持为空，不伪造三网结果。真正的三网结果必须来自对应运营商网络；GitHub-hosted Runner 只能代表自身网络环境。