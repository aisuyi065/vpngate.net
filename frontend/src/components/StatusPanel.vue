<script setup lang="ts">
import type { ConnectionStatus } from "../types";

defineProps<{
  status: ConnectionStatus;
}>();
</script>

<template>
  <section class="card status-panel">
    <div class="status-panel__header">
      <div>
        <p class="eyebrow">Runtime</p>
        <h2>Connection Status</h2>
      </div>
      <span class="pill" :data-state="status.state">{{ status.state }}</span>
    </div>
    <div class="status-grid">
      <div>
        <span class="label">Environment</span>
        <strong>{{ status.environment.toUpperCase() }}</strong>
      </div>
      <div>
        <span class="label">Connector</span>
        <strong>{{ status.mode }}</strong>
      </div>
      <div>
        <span class="label">Traffic Scope</span>
        <strong>{{ status.traffic_scope }}</strong>
      </div>
      <div>
        <span class="label">Current Public IP</span>
        <strong>{{ status.current_public_ip || "unknown" }}</strong>
      </div>
      <div>
        <span class="label">Connected IP</span>
        <strong>{{ status.connected_server_ip || "not connected" }}</strong>
      </div>
      <div>
        <span class="label">Connected Host</span>
        <strong>{{ status.connected_server_hostname || "not connected" }}</strong>
      </div>
    </div>
    <p v-if="status.warning" class="inline-message inline-message--warn">{{ status.warning }}</p>
    <p v-if="status.last_error" class="inline-message inline-message--error">{{ status.last_error }}</p>
  </section>
</template>

