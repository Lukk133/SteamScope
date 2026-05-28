<script setup lang="ts">
import { computed } from "vue";
import type { EChartsOption } from "echarts";
import BaseChart from "./BaseChart.vue";
import type { GenreStat } from "@/api/types";

const props = defineProps<{ data: GenreStat[]; loading?: boolean }>();

const option = computed<EChartsOption>(() => ({
  tooltip: { trigger: "axis" },
  grid: { left: 48, right: 16, top: 16, bottom: 64 },
  xAxis: {
    type: "category",
    data: props.data.map((g) => g.genre),
    axisLabel: { rotate: 35, interval: 0 },
  },
  yAxis: { type: "value" },
  series: [
    {
      type: "bar",
      name: "Liczba gier",
      data: props.data.map((g) => g.games_count),
      itemStyle: { color: "#818cf8" },
    },
  ],
}));
</script>

<template>
  <BaseChart :option="option" :empty="data.length === 0" :loading="loading" />
</template>
