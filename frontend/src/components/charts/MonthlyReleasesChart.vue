<script setup lang="ts">
import { computed } from "vue";
import type { EChartsOption } from "echarts";
import BaseChart from "./BaseChart.vue";
import type { MonthlyReleaseRow } from "@/api/types";

const props = defineProps<{ data: MonthlyReleaseRow[] }>();

const option = computed<EChartsOption>(() => {
  const labels = props.data.map((r) => `${r.year}-${String(r.month).padStart(2, "0")}`);
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 48, right: 16, top: 24, bottom: 48 },
    xAxis: { type: "category", data: labels, axisLabel: { rotate: 35 } },
    yAxis: { type: "value" },
    series: [
      {
        type: "line",
        smooth: true,
        data: props.data.map((r) => r.games_count),
        areaStyle: { opacity: 0.15 },
        itemStyle: { color: "#fbbf24" },
      },
    ],
  };
});
</script>

<template>
  <BaseChart :option="option" :empty="data.length === 0" />
</template>
