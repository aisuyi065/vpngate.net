# VPNGate / OpenVPN 模式部署说明

这份说明是给需要使用老牌 `VPNGate` 逻辑的人看的，不是给 `Hysteria 2` 那条 `hy2-native` 路线准备的。

## 这模式到底是干啥的

`openvpn` 模式会做这些事：

- 拉取公开 `VPNGate` 节点
- 给节点打分
- 在面板里展示节点列表
- 支持手动连接和自动连接

它不是简单的“显示列表”，它是真的要拉起 `OpenVPN` 并接管相关路由。

## 先决条件

这模式必须满足：

- 机器存在 `/dev/net/tun`
- 系统允许 `OpenVPN` 创建隧道
- 机器不是那种纯残血 `LXC + 无 TUN` 环境

先执行：

```bash
ls -l /dev/net/tun
```

如果这条命令报错，或者没有这个设备文件，就别折腾 `openvpn` 模式了，这台机器不适合。

## 正确安装命令

别走自动壳子，直接强制指定模式：

```bash
bash install.sh --mode openvpn --panel-pass 你的面板密码
```

## 不推荐这样装

```bash
./scripts/install-debian.sh
```

原因很简单：

- 这个脚本现在是通用入口
- 它可能根据宿主机条件自动选模式
- 你如果明确要 `openvpn`，就应该直接传 `--mode openvpn`

## 安装后应该看到什么

面板打开后，应该看到的是：

- `VPNGate` 节点列表
- `Refresh`
- `Connect`
- 自动连接国家控制

如果你看到的是 `Hysteria 2` 服务状态卡片，那说明当前不是 `openvpn` 模式，而是 `hy2-native` 模式。

## 基本验证命令

### 1. 看服务

```bash
systemctl status vpngate-controller.service --no-pager -l
```

### 2. 看健康检查

```bash
curl -i http://127.0.0.1:8000/health
```

### 3. 看运行模式

```bash
curl -i http://127.0.0.1:8000/api/status
```

返回里如果有：

```json
"mode":"openvpn"
```

那才说明你真切到 `VPNGate / OpenVPN` 模式了。

## 常见误区

### 误区 1：LXC 上也能强行跑

不一定。很多 LXC VPS 压根不给 `TUN`。

### 误区 2：看到项目叫 VPNGate Controller，就一定显示 VPNGate 列表

不对。这个项目现在有两种运行模式：

- `hy2-native`
- `openvpn`

UI 会跟着模式走。

### 误区 3：脚本装完但看不到节点，就是程序坏了

先别急着骂，先确认：

- `/dev/net/tun` 是否存在
- `.env` 里是不是 `VPNGATE_RUNTIME_MODE=openvpn`
- `api/status` 里返回的 `mode` 是不是 `openvpn`

## 一段可直接转发说明

把下面这段直接发给别人就行：

```text
如果你要用 VPNGate / OpenVPN 模式，不要跑自动壳子，直接执行：

bash install.sh --mode openvpn --panel-pass 你的面板密码

前提必须满足：
- 机器有 /dev/net/tun

先检查：
- ls -l /dev/net/tun

安装后验证：
- systemctl status vpngate-controller.service --no-pager -l
- curl -i http://127.0.0.1:8000/health
- curl -i http://127.0.0.1:8000/api/status

只有 mode=openvpn，才是真的 VPNGate 模式。
```
