# Hysteria 2 一键部署说明

这份说明是给运维、朋友、客户、同事直接转发用的，不需要他们先理解项目源码。

## 适用场景

适合以下环境：

- Ubuntu / Debian VPS
- LXC 容器 VPS
- 没有 `/dev/net/tun` 的机器
- 只需要 `Hysteria 2` 入站，不需要整机走 VPN

不适合以下环境：

- 想让宿主机所有流量都走 VPNGate / OpenVPN
- 没有 `systemd`

## 方案特点

- 不用 Docker
- 直接安装官方 `Hysteria 2`
- 自动生成项目面板
- 自动输出可用的 `hy2` 客户端链接
- 面板密码后续可在面板内直接修改，不用重新跑安装脚本
- 默认兼容常见社区脚本习惯：
  - `SNI=bing.com`
  - `masquerade=https://bing.com`
  - `insecure=1`

## 方案一：无域名，最快装好

适合先跑通、先能连。

```bash
bash install.sh --mode hy2-native --port 8443 --panel-pass 你的面板密码
```

如果你不传 `--panel-pass`，脚本也会自动生成一个面板密码，并在安装结束时打印出来。

执行完成后会输出一行：

```text
Hysteria URI: hysteria2://...
```

这就是客户端可直接导入的链接。

同时还会输出：

```text
Dashboard: http://外网IP:8000
Dashboard password: 你设置的密码
```

## 方案二：有域名，走 ACME 正式证书

适合长期稳定使用。

```bash
bash install.sh --mode hy2-native --domain 你的域名 --acme-email 你的邮箱 --port 443 --panel-pass 你的面板密码
```

示例：

```bash
bash install.sh --mode hy2-native --domain vpn.example.com --acme-email ops@example.com --port 443 --panel-pass panel-123456
```

## 必须放行的端口

至少放行这两个：

- `8000/tcp`：项目面板
- `8443/udp` 或你自己指定的 `udp` 端口：Hysteria 2

如果你用的是云厂商 VPS，还要同步放行安全组。

## 安装后检查

### 1. 看 Hysteria 2 是否正常

```bash
systemctl status hysteria-server.service
```

### 2. 看控制面板是否正常

```bash
systemctl status vpngate-controller.service
```

### 3. 看 Hysteria 2 日志

```bash
journalctl --no-pager -e -u hysteria-server.service
```

### 4. 打开面板

浏览器访问：

```text
http://你的外网 IP:8000
```

打开后只需要输入密码，不需要用户名。

## 默认输出链接长什么样

无域名、自签模式下，默认会生成类似下面的链接：

```text
hysteria2://密码@你的服务器IP:8443/?sni=bing.com&insecure=1#VPNGate-Hysteria2
```

注意：

- 这里的 `8443` 是 `UDP` 端口
- 默认 `sni=bing.com`
- 默认 `insecure=1`

## 常见问题

### Q1：为什么客户端连不上？

先检查这几件事：

- `udp` 端口有没有放行
- `hysteria-server.service` 是否为 `active`
- 你的 VPS 提供商有没有拦截 `udp`

### Q2：为什么不是整机代理？

因为这个模式本来就是 `hy2-native`，目标是：

- 只处理 `Hysteria 2` 进来的流量
- 不改宿主机默认路由
- 兼容 `LXC + 无 TUN`

### Q3：没有域名能不能用？

能用。默认就是给无域名场景准备的。

### Q4：有域名是不是更好？

是。建议长期使用时改成：

- `--domain`
- `--acme-email`
- `--port 443`

## 一段可以直接转发给别人的最短说明

把下面这段原样发给对方就行：

```text
在服务器项目目录执行：

bash install.sh --mode hy2-native --port 8443 --panel-pass 你的面板密码

安装完成后会打印 Hysteria URI: hysteria2://...
以及 Dashboard: http://外网IP:8000

记得放行：
- 8000/tcp
- 8443/udp

检查服务：
- systemctl status hysteria-server.service
- systemctl status vpngate-controller.service

看日志：
- journalctl --no-pager -e -u hysteria-server.service
```
