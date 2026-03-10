export interface IpQualityRecord {
  ip: string;
  provider?: string;
  quality_class: "residential" | "hosting" | "unknown";
  is_datacenter?: boolean;
  is_proxy?: boolean;
  is_vpn?: boolean;
  is_mobile?: boolean;
  country_code?: string | null;
  company_name?: string | null;
  company_type?: string | null;
  asn_org?: string | null;
  asn_type?: string | null;
  confidence_note?: string | null;
}

export interface ServerItem {
  server_id: string;
  hostname: string;
  ip: string;
  score: number;
  ping: number;
  speed: number;
  country_long: string;
  country_code: string;
  num_vpn_sessions: number;
  uptime: number;
  total_users: number;
  total_traffic: number;
  log_type: string;
  operator: string;
  message: string;
  supports_openvpn: boolean;
  supports_softether: boolean;
  supports_l2tp: boolean;
  supports_sstp: boolean;
  openvpn_tcp_port?: number | null;
  openvpn_udp_port?: number | null;
  quality_score: number;
  is_connected: boolean;
  ip_quality?: IpQualityRecord | null;
}

export interface ConnectionStatus {
  state: "idle" | "connecting" | "connected" | "degraded" | "reconnecting" | "failed";
  mode: string;
  environment: "linux" | "wsl";
  traffic_scope: string;
  auto_mode_enabled: boolean;
  allowed_countries: string[];
  connected_server_ip?: string | null;
  connected_server_country?: string | null;
  connected_server_hostname?: string | null;
  current_public_ip?: string | null;
  last_error?: string | null;
  warning?: string | null;
  last_refresh_at?: string | null;
}

export interface ServerListResponse {
  items: ServerItem[];
  total: number;
}

export interface HysteriaStatus {
  runtime_mode: string;
  installed: boolean;
  service_name: string;
  service_state: string;
  enabled: boolean;
  listen_host: string;
  listen_port: number;
  tls_mode: "self_signed" | "acme";
  domain?: string | null;
  masquerade_url: string;
  config_path: string;
  warning?: string | null;
}

export interface HysteriaClientConfig {
  server: string;
  auth: string;
  tls: {
    sni?: string;
    insecure?: boolean;
  };
  uri: string;
}

export interface HysteriaLogResponse {
  items: string[];
}

export interface DashboardAuthStatus {
  enabled: boolean;
  authenticated: boolean;
}
