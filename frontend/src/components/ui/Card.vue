<script setup lang="ts">
import { cn } from "@/lib/utils";

defineProps<{ title?: string; class?: string }>();
</script>

<template>
  <div
    :class="cn('rounded-xl border border-border bg-card text-card-foreground shadow-sm', $props.class)"
  >
    <div v-if="title" class="border-b border-border px-4 py-3">
      <h3 class="text-sm font-semibold tracking-tight">{{ title }}</h3>
    </div>
    <div class="p-4">
      <slot />
    </div>
  </div>
</template>
