<script setup lang="ts">
import { computed } from "vue";
import type { EChartsOption } from "echarts";
import BaseChart from "./BaseChart.vue";
import type { SentimentRow } from "@/api/types";

const props = defineProps<{ data: SentimentRow[]; loading?: boolean }>();

const option = computed<EChartsOption>(() => {
  const genres = [...new Set(props.data.map((r) => r.genre))];
  const labels = [...new Set(props.data.map((r) => r.sentiment_label))];
  const series = labels.map((label) => ({
    name: label,
    type: "bar" as const,
    stack: "sentiment",
    data: genres.map((genre) => {
      const match = props.data.find((r) => r.genre === genre && r.sentiment_label === label);
      return match ? match.games_count : 0;
    }),
  }));
  return {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { top: 0, textStyle: { color: "#cbd5e1" } },
    grid: { left: 48, right: 16, top: 32, bottom: 64 },
    xAxis: { type: "category", data: genres, axisLabel: { rotate: 35, interval: 0 } },
    yAxis: { type: "value" },
    series,
  };
});
</script>

<template>
  <BaseChart :option="option" :empty="data.length === 0" :loading="loading" />
</template>
