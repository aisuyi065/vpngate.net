<script setup lang="ts">
import { shallowRef } from "vue";

defineProps<{
  busy: boolean;
  errorMessage: string;
}>();

const emit = defineEmits<{
  login: [password: string];
}>();

const password = shallowRef("");

function submit() {
  emit("login", password.value);
}

function updatePassword(value: string) {
  password.value = value;
}
</script>

<template>
  <section class="card login-card">
    <div class="login-card__header">
      <p class="eyebrow">Dashboard Lock</p>
      <h2>输入面板密码</h2>
    </div>

    <p class="login-card__copy">
      这个面板现在只接受密码访问，不需要用户名，别瞎填那些有的没的。
    </p>

    <form class="login-card__form" @submit.prevent="submit">
      <label class="field">
        <span>Password</span>
        <input
          type="password"
          class="field__input"
          :disabled="busy"
          :value="password"
          autocomplete="current-password"
          @input="updatePassword(($event.target as HTMLInputElement).value)"
        />
      </label>
      <button class="button button--primary" :disabled="busy || !password.trim()">
        {{ busy ? "验证中..." : "进入面板" }}
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
