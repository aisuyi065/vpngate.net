import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HysteriaPanel from "../src/components/HysteriaPanel.vue";

describe("HysteriaPanel", () => {
  it("renders service metadata, client URI, and restart action", async () => {
    const wrapper = mount(HysteriaPanel, {
      props: {
        busy: false,
        status: {
          runtime_mode: "hy2-native",
          installed: true,
          service_name: "hysteria-server.service",
          service_state: "active",
          enabled: true,
          listen_host: "0.0.0.0",
          listen_port: 8443,
          tls_mode: "self_signed",
          domain: null,
          masquerade_url: "https://bing.com",
          config_path: "/etc/hysteria/config.yaml",
          warning: "Self-signed mode",
        },
        clientConfig: {
          server: "gateway.example.com:8443",
          auth: "secret-pass",
          tls: {
            sni: "bing.com",
            insecure: true,
          },
          uri: "hysteria2://secret-pass@gateway.example.com:8443/?sni=bing.com&insecure=1#VPNGate-Hysteria2",
        },
        logs: ["Booted hysteria", "Listening on UDP 8443"],
      },
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain("Hysteria 2 Service");
    expect(wrapper.text()).toContain("hysteria-server.service");
    expect(wrapper.text()).toContain("gateway.example.com:8443");
    expect(wrapper.text()).toContain("hysteria2://");
    expect(wrapper.text()).toContain("Restart Service");
    expect(wrapper.text()).toContain("Listening on UDP 8443");
  });
});
