import type {
  ConnectionStatus,
  HysteriaClientConfig,
  HysteriaLogResponse,
  HysteriaStatus,
  ServerListResponse,
} from "../types";

async function requestJson<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  const response = await fetch(input, {
    headers: {
      "Content-Type": "application/json",
    },
    ...init,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

export function getStatus(): Promise<ConnectionStatus> {
  return requestJson<ConnectionStatus>("/api/status");
}

export function getServers(): Promise<ServerListResponse> {
  return requestJson<ServerListResponse>("/api/servers");
}

export function refreshServers(): Promise<{ refreshed: boolean; servers: number }> {
  return requestJson("/api/refresh", { method: "POST" });
}

export function connectServer(serverId: string): Promise<ConnectionStatus> {
  return requestJson(`/api/connect/${encodeURIComponent(serverId)}`, {
    method: "POST",
  });
}

export function disconnectServer(): Promise<ConnectionStatus> {
  return requestJson("/api/disconnect", { method: "POST" });
}

export function updateAutoMode(
  enabled: boolean,
  allowedCountries: string[],
): Promise<ConnectionStatus> {
  return requestJson("/api/auto-mode", {
    method: "POST",
    body: JSON.stringify({
      enabled,
      allowed_countries: allowedCountries,
    }),
  });
}

export function getHysteriaStatus(): Promise<HysteriaStatus> {
  return requestJson<HysteriaStatus>("/api/hysteria/status");
}

export function getHysteriaClientConfig(): Promise<HysteriaClientConfig> {
  return requestJson<HysteriaClientConfig>("/api/hysteria/client-config");
}

export function getHysteriaLogs(): Promise<HysteriaLogResponse> {
  return requestJson<HysteriaLogResponse>("/api/hysteria/logs");
}

export function restartHysteria(): Promise<HysteriaStatus> {
  return requestJson<HysteriaStatus>("/api/hysteria/restart", {
    method: "POST",
  });
}
