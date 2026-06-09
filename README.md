# 🚀 Clash & V2Ray 节点订阅自动收集器 (GitHub Actions)

每日自动搜集全网免费代理节点，优先采集**非 GitHub 直连源**，聚合去重后输出**双格式订阅文件**，永久零成本托管于 GitHub Actions。

---

## 🌟 核心特性

| 特性 | 说明 |
|------|------|
| **三轮采集** | 优先获取 "优先源"（非 raw.githubusercontent.com）→ 常规源 → 备用补充源 |
| **双格式输出** | 同步输出 **Clash YAML** (`clashnode.yaml`) 和 **V2Ray base64** (`v2raynode.txt`) |
| **全协议支持** | `vmess://` `vless://` `ss://` `trojan://` `hysteria2://` `hy2://` `socks5://` `http://` 双向互转 |
| **高并发** | 20线程并发验证，自动排除 404、无效页面 |
| **零成本** | 完全托管于 GitHub Actions，无需任何服务器 |

---

## 📁 项目文件

| 文件 | 说明 |
|------|------|
| `collect.py` | ⚙️ 核心采集+转换程序 |
| `.github/workflows/collect.yml` | 🔄 自动工作流 (每日 08:30 UTC+8) |
| `clashnode.yaml` | 📦 生成的 Clash 订阅文件 (仅 proxies) |
| `v2raynode.txt` | 📦 生成的 V2Ray 订阅文件 (base64) |

---

## 🛠️ 部署步骤

### 1. 新建 GitHub 仓库 → 上传本目录全部文件

### 2. 开启 Actions 写权限
`仓库 Settings → Actions → General → Workflow permissions → Read and write permissions`

### 3. 点击 Actions → Run workflow 手动触发一次

执行完毕后仓库根目录生成：
- `clashnode.yaml` — Clash 标准订阅
- `v2raynode.txt` — V2Ray 标准订阅

---

## 🔗 订阅引用地址

### Clash
```
https://raw.githubusercontent.com/<你的用户名>/<仓库名>/refs/heads/main/clashnode.yaml
```

### V2Ray
```
https://raw.githubusercontent.com/<你的用户名>/<仓库名>/refs/heads/main/v2raynode.txt
```

### 在 subs-check config.yaml 中引用
```yaml
sub-urls:
  - "https://raw.githubusercontent.com/<你的用户名>/<仓库名>/refs/heads/main/clashnode.yaml"
  - "https://raw.githubusercontent.com/<你的用户名>/<仓库名>/refs/heads/main/v2raynode.txt"
```
