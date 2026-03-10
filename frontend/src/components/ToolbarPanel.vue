<script setup lang="ts">
defineProps<{
  busy: boolean;
  autoModeEnabled: boolean;
  allowedCountriesInput: string;
}>();

const emit = defineEmits<{
  refresh: [];
  disconnect: [];
  toggleAutoMode: [value: boolean];
  updateAllowedCountries: [value: string];
  save: [];
}>();
</script>

<template>
  <section class="card toolbar-panel">
    <div class="toolbar-panel__group">
      <button class="button button--primary" :disabled="busy" @click="emit('refresh')">
        Refresh
      </button>
      <button class="button" :disabled="busy" @click="emit('disconnect')">Disconnect</button>
    </div>
    <div class="toolbar-panel__group toolbar-panel__group--form">
      <label class="switch">
        <input
          type="checkbox"
          :checked="autoModeEnabled"
          @change="emit('toggleAutoMode', ($event.target as HTMLInputElement).checked)"
        />
        <span>Auto-connect</span>
      </label>
      <label class="field">
        <span>Allowed Countries</span>
        <input
          class="field__input"
          :value="allowedCountriesInput"
          placeholder="JP,KR,TW"
          @input="emit('updateAllowedCountries', ($event.target as HTMLInputElement).value)"
        />
      </label>
      <button class="button button--accent" :disabled="busy" @click="emit('save')">
        Save Auto Mode
      </button>
    </div>
  </section>
</template>
