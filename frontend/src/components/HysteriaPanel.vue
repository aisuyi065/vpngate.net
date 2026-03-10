<script setup lang="ts">
import type { HysteriaClientConfig, HysteriaStatus } from "../types";

defineProps<{
  busy: boolean;
  status: HysteriaStatus | null;
  clientConfig: HysteriaClientConfig | null;
  logs: string[];
}>();

const emit = defineEmits<{
  restart: [];
}>();
</script>

<template>
  <section class="card hysteria-panel">
    <div class="hysteria-panel__header">
      <div>
        <p class="eyebrow">Hysteria 2</p>
        <h2>Hysteria 2 Service</h2>
      </div>
      <button class="button button--accent" :disabled="busy" @click="emit('restart')">
        {{ busy ? "Restarting..." : "Restart Service" }}
      </button>
    </div>

    <div v-if="status" class="hysteria-panel__grid">
      <div class="hysteria-panel__item">
        <span class="label">Service</span>
        <strong>{{ status.service_name }}</strong>
        <span class="subtle">{{ status.service_state }}</span>
      </div>
      <div class="hysteria-panel__item">
        <span class="label">Listen</span>
        <strong>{{ status.listen_host }}:{{ status.listen_port }}</strong>
        <span class="subtle">{{ status.tls_mode }}</span>
      </div>
      <div class="hysteria-panel__item">
        <span class="label">Masquerade</span>
        <strong>{{ status.masquerade_url }}</strong>
        <span class="subtle">{{ status.config_path }}</span>
      </div>
      <div class="hysteria-panel__item">
        <span class="label">Client Target</span>
        <strong>{{ clientConfig?.server || "not ready" }}</strong>
        <span class="subtle">SNI {{ clientConfig?.tls?.sni || "auto" }}</span>
      </div>
    </div>

    <p v-if="status?.warning" class="inline-message inline-message--warn">
      {{ status.warning }}
    </p>

    <div v-if="clientConfig" class="hysteria-panel__section">
      <span class="label">Connection URI</span>
      <code class="hysteria-panel__uri">{{ clientConfig.uri }}</code>
    </div>

    <div class="hysteria-panel__section">
      <span class="label">Recent Logs</span>
      <pre class="hysteria-panel__logs">{{ logs.length ? logs.join("\n") : "No logs yet." }}</pre>
    </div>
  </section>
</template>

<style scoped>
.hysteria-panel {
  display: grid;
  gap: 1rem;
}

.hysteria-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.hysteria-panel__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}

.hysteria-panel__item {
  display: grid;
  gap: 0.35rem;
}

.hysteria-panel__section {
  display: grid;
  gap: 0.45rem;
}

.hysteria-panel__uri,
.hysteria-panel__logs {
  overflow-x: auto;
  padding: 0.95rem;
  border-radius: 14px;
  border: 1px solid rgba(153, 179, 255, 0.16);
  background: rgba(6, 11, 22, 0.88);
  color: #dbe7ff;
  font-size: 0.9rem;
  line-height: 1.5;
}

.hysteria-panel__uri {
  white-space: nowrap;
}

.hysteria-panel__logs {
  margin: 0;
  white-space: pre-wrap;
}
</style>
