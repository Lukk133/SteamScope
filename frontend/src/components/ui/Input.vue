<script setup lang="ts">
import { cn } from "@/lib/utils";

defineProps<{ modelValue?: string; placeholder?: string; class?: string }>();
defineEmits<{ "update:modelValue": [value: string] }>();
</script>

<template>
  <input
    :value="modelValue"
    :placeholder="placeholder"
    :class="
      cn(
        'flex h-10 w-full rounded-md border border-border bg-background px-3 py-2 text-sm',
        'placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary',
        $props.class,
      )
    "
    @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
  />
</template>
