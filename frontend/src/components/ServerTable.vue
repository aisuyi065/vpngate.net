<script setup lang="ts">
import { formatQuality, formatUptime, formatUsers, supportedMethods } from "../lib/format";
import type { ServerItem } from "../types";

defineProps<{
  servers: ServerItem[];
  busyServerId: string | null;
}>();

const emit = defineEmits<{
  connect: [serverId: string];
}>();
</script>

<template>
  <section class="card table-panel">
    <div class="table-panel__header">
      <div>
        <p class="eyebrow">Inventory</p>
        <h2>VPNGate Residential Candidates</h2>
      </div>
      <span class="table-panel__count">{{ servers.length }} servers</span>
    </div>
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Country</th>
            <th>IP Address</th>
            <th>Supported Methods</th>
            <th>IP Quality</th>
            <th>Uptime</th>
            <th>Total Users</th>
            <th>Connected</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="server in servers" :key="server.server_id" :class="{ connected: server.is_connected }">
            <td>
              <strong>{{ server.country_long || server.country_code }}</strong>
              <span class="subtle">{{ server.country_code }}</span>
            </td>
            <td>
              <strong>{{ server.ip }}</strong>
              <span class="subtle">{{ server.hostname }}</span>
            </td>
            <td>{{ supportedMethods(server) }}</td>
            <td>
              <strong>{{ formatQuality(server) }}</strong>
              <span class="subtle">score {{ server.quality_score }}</span>
            </td>
            <td>{{ formatUptime(server.uptime) }}</td>
            <td>{{ formatUsers(server.total_users) }}</td>
            <td>
              <span class="pill" :data-state="server.is_connected ? 'connected' : 'idle'">
                {{ server.is_connected ? "Yes" : "No" }}
              </span>
            </td>
            <td>
              <button
                class="button button--table"
                :disabled="busyServerId === server.server_id"
                @click="emit('connect', server.server_id)"
              >
                {{ busyServerId === server.server_id ? "Connecting..." : "Connect" }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

