# CF Best IP

自动扫描 Cloudflare IPv4 地址并生成适用于 Sub-Store / sing-box 的优选结果。

## 输出

- `results/all.txt` — 全部通过测试的优选 IP
- `results/443.txt` — 443 端口结果
- `results/ctcc.txt` — 电信结果（当前 GitHub Runner 测试池）
- `results/cuсc.txt` — 联通结果（当前 GitHub Runner 测试池）
- `results/cmcc.txt` — 移动结果（当前 GitHub Runner 测试池）

> GitHub-hosted Runner 本身不位于中国三网，因此不能把它测出的结果冒充中国电信/联通/移动本地实测。三网文件目前采用同一基础质量池，为后续接入中国境内探针保留接口。

## 工作方式

1. 获取 Cloudflare 官方 IPv4 网段
2. 展开候选 IP
3. 并发进行 TCP 443 + TLS 握手测试
4. 按连接延迟排序
5. 生成 TXT
6. GitHub Actions 定时更新 GitHub Pages

默认每 3 小时运行一次，也支持手动运行。

## GitHub Pages

启用 Pages 后：

`https://Mk8gg.github.io/test/results/all.txt`

具体 Pages 地址以仓库设置显示为准。

## 配置

环境变量：

- `PORT` 默认 `443`
- `MAX_IPS_PER_CIDR` 默认 `256`
- `TOP_N` 默认 `50`
- `TIMEOUT_MS` 默认 `2500`

后续可以增加中国大陆电信/联通/移动探针，再将三网结果真正分开。
