<script setup lang="ts">
import { computed, onMounted, ref, shallowRef, watch } from "vue";

import {
  changeDashboardPassword,
  connectServer,
  disconnectServer,
  getDashboardAuthStatus,
  getHysteriaClientConfig,
  getHysteriaLogs,
  getHysteriaStatus,
  getServers,
  getStatus,
  loginDashboard,
  logoutDashboard,
  refreshServers,
  restartHysteria,
  updateAutoMode,
} from "./lib/api";
import { supportedMethods } from "./lib/format";
import type {
  ConnectionStatus,
  DashboardAuthStatus,
  HysteriaClientConfig,
  HysteriaStatus,
  ServerItem,
} from "./types";
import DashboardLoginCard from "./components/DashboardLoginCard.vue";
import DashboardPasswordCard from "./components/DashboardPasswordCard.vue";
import HysteriaPanel from "./components/HysteriaPanel.vue";
import ServerTable from "./components/ServerTable.vue";
import StatusPanel from "./components/StatusPanel.vue";
import ToolbarPanel from "./components/ToolbarPanel.vue";

const seedStatus: ConnectionStatus = {
  state: "idle",
  mode: "mock",
  environment: "wsl",
  traffic_scope: "wsl",
  auto_mode_enabled: true,
  allowed_countries: ["JP", "KR"],
  connected_server_ip: null,
  connected_server_country: null,
  connected_server_hostname: null,
  current_public_ip: "198.51.100.10",
  last_error: null,
  warning: "WSL mode only controls WSL process traffic, not the Windows host.",
  last_refresh_at: null,
};

const seedServers: ServerItem[] = [
  {
    server_id: "1.2.3.4",
    hostname: "public-vpn-1",
    ip: "1.2.3.4",
    score: 100,
    ping: 15,
    speed: 2000000,
    country_long: "Japan",
    country_code: "JP",
    num_vpn_sessions: 12,
    uptime: 3600,
    total_users: 500,
    total_traffic: 1111,
    log_type: "2weeks",
    operator: "tester",
    message: "",
    supports_openvpn: true,
    supports_softether: true,
    supports_l2tp: true,
    supports_sstp: true,
    openvpn_tcp_port: 443,
    openvpn_udp_port: 1194,
    quality_score: 88,
    is_connected: false,
    ip_quality: {
      ip: "1.2.3.4",
      quality_class: "residential",
    },
  },
];

const status = ref<ConnectionStatus>(seedStatus);
const servers = ref<ServerItem[]>(seedServers);
const hysteriaStatus = ref<HysteriaStatus | null>(null);
const hysteriaClientConfig = ref<HysteriaClientConfig | null>(null);
const hysteriaLogs = ref<string[]>([]);
const dashboardAuthStatus = ref<DashboardAuthStatus>({
  enabled: false,
  authenticated: true,
});
const busy = shallowRef(false);
const busyServerId = shallowRef<string | null>(null);
const hysteriaBusy = shallowRef(false);
const loginBusy = shallowRef(false);
const dashboardPasswordBusy = shallowRef(false);
const showDashboardPasswordCard = shallowRef(false);
const errorMessage = shallowRef("");
const dashboardPasswordErrorMessage = shallowRef("");
const allowedCountriesInput = shallowRef(seedStatus.allowed_countries.join(","));

const isHy2Mode = computed(() => status.value.mode === "hy2-native");
const isDashboardLocked = computed(
  () => dashboardAuthStatus.value.enabled && !dashboardAuthStatus.value.authenticated,
);

const heroTitle = computed(() => {
  return isHy2Mode.value ? "Hysteria 2 Edge Dashboard" : "Residential Exit Dashboard";
});

const heroCopy = computed(() => {
  if (isHy2Mode.value) {
    return "Manage the local Hysteria 2 service, keep client traffic proxied, and leave the host machine routing untouched.";
  }
  return "Watch live candidates, lock manual routes, and keep WSL or Debian traffic pointed at the best residential-looking VPNGate node.";
});

watch(
  () => status.value.allowed_countries,
  (countries) => {
    allowedCountriesInput.value = countries.join(",");
  },
  { immediate: true },
);

const summary = computed(() => {
  if (isHy2Mode.value) {
    if (!hysteriaStatus.value) {
      return "Loading local Hysteria 2 service state.";
    }
    if (hysteriaStatus.value.service_state === "active") {
      return `Hysteria 2 is serving proxied traffic on UDP ${hysteriaStatus.value.listen_port} without touching host routing.`;
    }
    return `Hysteria 2 is currently ${hysteriaStatus.value.service_state}.`;
  }
  const connected = servers.value.find((server) => server.is_connected);
  if (!connected) {
    return "No active tunnel. Pick a residential node or enable auto-connect.";
  }
  return `Connected to ${connected.country_long} via ${supportedMethods(connected)}.`;
});

function parseCountryInput(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim().toUpperCase())
    .filter(Boolean);
}

function handleToggleAutoMode(value: boolean) {
  status.value.auto_mode_enabled = value;
}

function handleAllowedCountriesInput(value: string) {
  allowedCountriesInput.value = value;
}

async function loadStatus() {
  status.value = await getStatus();
}

async function loadDashboardAuthStatus() {
  dashboardAuthStatus.value = await getDashboardAuthStatus();
}

async function loadServers() {
  const response = await getServers();
  servers.value = response.items.length > 0 ? response.items : seedServers;
}

async function loadHysteria() {
  const [service, client, logs] = await Promise.all([
    getHysteriaStatus(),
    getHysteriaClientConfig(),
    getHysteriaLogs(),
  ]);
  hysteriaStatus.value = service;
  hysteriaClientConfig.value = client;
  hysteriaLogs.value = logs.items;
}

async function loadAll() {
  try {
    errorMessage.value = "";
    busy.value = true;
    await loadDashboardAuthStatus();
    if (isDashboardLocked.value) {
      return;
    }
    await Promise.all([loadStatus(), loadServers(), loadHysteria()]);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Failed to load dashboard data.";
  } finally {
    busy.value = false;
  }
}

async function handleRefresh() {
  try {
    busy.value = true;
    errorMessage.value = "";
    await refreshServers();
    await loadAll();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Refresh failed.";
  } finally {
    busy.value = false;
  }
}

async function handleConnect(serverId: string) {
  try {
    busyServerId.value = serverId;
    errorMessage.value = "";
    status.value = await connectServer(serverId);
    await loadServers();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Connect request failed.";
  } finally {
    busyServerId.value = null;
  }
}

async function handleDisconnect() {
  try {
    busy.value = true;
    errorMessage.value = "";
    status.value = await disconnectServer();
    await loadServers();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Disconnect request failed.";
  } finally {
    busy.value = false;
  }
}

async function handleSaveAutoMode() {
  try {
    busy.value = true;
    errorMessage.value = "";
    status.value = await updateAutoMode(
      status.value.auto_mode_enabled,
      parseCountryInput(allowedCountriesInput.value),
    );
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Saving auto mode failed.";
  } finally {
    busy.value = false;
  }
}

async function handleRestartHysteria() {
  try {
    hysteriaBusy.value = true;
    errorMessage.value = "";
    await restartHysteria();
    await Promise.all([loadStatus(), loadHysteria()]);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Restarting Hysteria failed.";
  } finally {
    hysteriaBusy.value = false;
  }
}

async function handleDashboardLogin(password: string) {
  try {
    loginBusy.value = true;
    errorMessage.value = "";
    dashboardAuthStatus.value = await loginDashboard(password);
    await loadAll();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "面板密码验证失败。";
  } finally {
    loginBusy.value = false;
  }
}

async function handleDashboardLogout() {
  await logoutDashboard();
  dashboardAuthStatus.value = await getDashboardAuthStatus();
  showDashboardPasswordCard.value = false;
}

function handleToggleDashboardPasswordCard() {
  showDashboardPasswordCard.value = !showDashboardPasswordCard.value;
  dashboardPasswordErrorMessage.value = "";
}

async function handleChangeDashboardPassword(password: string) {
  try {
    dashboardPasswordBusy.value = true;
    dashboardPasswordErrorMessage.value = "";
    dashboardAuthStatus.value = await changeDashboardPassword(password);
    showDashboardPasswordCard.value = false;
  } catch (error) {
    dashboardPasswordErrorMessage.value =
      error instanceof Error ? error.message : "更新面板密码失败。";
  } finally {
    dashboardPasswordBusy.value = false;
  }
}

onMounted(async () => {
  if (typeof fetch !== "function") {
    return;
  }
  await loadAll();
});
</script>

<template>
  <main class="shell">
    <section class="hero">
      <p class="eyebrow">VPNGate Controller</p>
      <h1>{{ heroTitle }}</h1>
      <p class="hero__copy">{{ heroCopy }}</p>
      <p class="hero__summary">{{ summary }}</p>
    </section>

    <DashboardLoginCard
      v-if="isDashboardLocked"
      :busy="loginBusy"
      :error-message="errorMessage"
      @login="handleDashboardLogin"
    />

    <template v-else>
      <StatusPanel :status="status" />

      <section class="toolbar-panel toolbar-panel--top card">
        <div class="toolbar-panel__group">
          <button
            v-if="dashboardAuthStatus.enabled"
            class="button"
            @click="handleToggleDashboardPasswordCard"
          >
            {{ showDashboardPasswordCard ? "收起密码修改" : "修改面板密码" }}
          </button>
          <button class="button" @click="handleDashboardLogout">锁定面板</button>
        </div>
      </section>

      <DashboardPasswordCard
        v-if="showDashboardPasswordCard"
        :busy="dashboardPasswordBusy"
        :error-message="dashboardPasswordErrorMessage"
        @change-password="handleChangeDashboardPassword"
      />

      <HysteriaPanel
        v-if="hysteriaStatus"
        :busy="hysteriaBusy"
        :status="hysteriaStatus"
        :client-config="hysteriaClientConfig"
        :logs="hysteriaLogs"
        @restart="handleRestartHysteria"
      />

      <ToolbarPanel
        v-if="!isHy2Mode"
        :busy="busy"
        :auto-mode-enabled="status.auto_mode_enabled"
        :allowed-countries-input="allowedCountriesInput"
        @refresh="handleRefresh"
        @disconnect="handleDisconnect"
        @save="handleSaveAutoMode"
        @toggle-auto-mode="handleToggleAutoMode"
        @update-allowed-countries="handleAllowedCountriesInput"
      />

      <p v-if="errorMessage" class="inline-message inline-message--error">{{ errorMessage }}</p>

      <ServerTable
        v-if="!isHy2Mode"
        :servers="servers"
        :busy-server-id="busyServerId"
        @connect="handleConnect"
      />
    </template>
  </main>
</template>
