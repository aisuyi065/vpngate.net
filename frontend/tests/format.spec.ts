import { describe, expect, it } from "vitest";

import { formatUptime, supportedMethods } from "../src/lib/format";
import type { ServerItem } from "../src/types";

describe("format helpers", () => {
  it("formats uptime into compact labels", () => {
    expect(formatUptime(90)).toBe("1m");
    expect(formatUptime(3600)).toBe("1h 0m");
    expect(formatUptime(90000)).toBe("1d 1h");
  });

  it("joins supported methods in a stable order", () => {
    const server = {
      server_id: "1.2.3.4",
      hostname: "sample",
      ip: "1.2.3.4",
      score: 0,
      ping: 0,
      speed: 0,
      country_long: "Japan",
      country_code: "JP",
      num_vpn_sessions: 0,
      uptime: 0,
      total_users: 0,
      total_traffic: 0,
      log_type: "",
      operator: "",
      message: "",
      supports_openvpn: true,
      supports_softether: true,
      supports_l2tp: false,
      supports_sstp: true,
      quality_score: 0,
      is_connected: false,
      ip_quality: null,
    } as ServerItem;

    expect(supportedMethods(server)).toBe("OpenVPN, SoftEther, MS-SSTP");
  });
});
