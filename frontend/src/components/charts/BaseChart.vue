<script setup lang="ts">
import VChart from "vue-echarts";
import type { EChartsOption } from "echarts";
import "@/echarts";

defineProps<{
  option: EChartsOption;
  empty?: boolean;
  loading?: boolean;
  height?: string;
}>();
</script>

<template>
  <div :style="{ height: height ?? '320px' }" class="w-full">
    <div
      v-if="loading"
      class="h-full w-full animate-pulse rounded-md bg-muted"
      aria-label="Ładowanie wykresu"
    />
    <div
      v-else-if="empty"
      class="flex h-full items-center justify-center text-sm text-muted-foreground"
    >
      Brak danych — uruchom pipeline ingestion/ETL.
    </div>
    <VChart v-else :option="option" autoresize class="h-full w-full" />
  </div>
</template>
