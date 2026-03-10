<script setup lang="ts">
import { shallowRef } from "vue";

defineProps<{
  busy: boolean;
  errorMessage: string;
}>();

const emit = defineEmits<{
  changePassword: [password: string];
}>();

const password = shallowRef("");

function submit() {
  emit("changePassword", password.value);
}

function updatePassword(value: string) {
  password.value = value;
}
</script>

<template>
  <section class="card login-card">
    <div class="login-card__header">
      <p class="eyebrow">Dashboard Password</p>
      <h2>修改面板密码</h2>
    </div>

    <p class="login-card__copy">
      这里只改面板访问密码，不影响 `Hysteria 2` 的客户端密码，别俩东西整串味了。
    </p>

    <form class="login-card__form" @submit.prevent="submit">
      <label class="field">
        <span>New Password</span>
        <input
          type="password"
          class="field__input"
          :disabled="busy"
          :value="password"
          autocomplete="new-password"
          @input="updatePassword(($event.target as HTMLInputElement).value)"
        />
      </label>
      <button class="button button--accent" :disabled="busy || !password.trim()">
        {{ busy ? "更新中..." : "更新密码" }}
      </button>
    </form>

    <p v-if="errorMessage" class="inline-message inline-message--error">{{ errorMessage }}</p>
  </section>
</template>

<style scoped>
.login-card {
  width: min(520px, 100%);
  margin: 0 auto;
  display: grid;
  gap: 1rem;
}

.login-card__header,
.login-card__form {
  display: grid;
  gap: 0.85rem;
}

.login-card__copy {
  margin: 0;
  color: #c8d5f4;
  line-height: 1.6;
}
</style>
