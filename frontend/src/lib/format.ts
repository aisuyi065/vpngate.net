import type { ServerItem } from "../types";

export function formatUptime(seconds: number): string {
  const total = Math.max(0, seconds || 0);
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);

  if (days > 0) {
    return `${days}d ${hours}h`;
  }
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

export function formatUsers(count: number): string {
  return new Intl.NumberFormat("en-US").format(count || 0);
}

export function formatQuality(server: ServerItem): string {
  return server.ip_quality?.quality_class ?? "unknown";
}

export function supportedMethods(server: ServerItem): string {
  const methods = [];
  if (server.supports_openvpn) methods.push("OpenVPN");
  if (server.supports_softether) methods.push("SoftEther");
  if (server.supports_l2tp) methods.push("L2TP/IPsec");
  if (server.supports_sstp) methods.push("MS-SSTP");
  return methods.join(", ") || "Unknown";
}

