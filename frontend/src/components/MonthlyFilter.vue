<script setup lang="ts">
import { ref } from "vue";
import Input from "@/components/ui/Input.vue";

const emit = defineEmits<{ apply: [from: number | undefined, to: number | undefined] }>();
const from = ref("");
const to = ref("");

function apply(): void {
  emit("apply", from.value ? Number(from.value) : undefined, to.value ? Number(to.value) : undefined);
}
</script>

<template>
  <div class="mb-3 flex items-center gap-2">
    <Input v-model="from" placeholder="Rok od" class="w-28" />
    <Input v-model="to" placeholder="Rok do" class="w-28" />
    <button
      class="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground"
      @click="apply"
    >
      Filtruj
    </button>
  </div>
</template>
