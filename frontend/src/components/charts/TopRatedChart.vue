<script setup lang="ts">
import { computed } from "vue";
import type { EChartsOption } from "echarts";
import BaseChart from "./BaseChart.vue";
import type { TopRatedGame } from "@/api/types";

const props = defineProps<{ data: TopRatedGame[] }>();

const option = computed<EChartsOption>(() => {
  const sorted = [...props.data].sort(
    (a, b) => (a.rating_score ?? 0) - (b.rating_score ?? 0),
  );
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 140, right: 16, top: 16, bottom: 24 },
    xAxis: { type: "value", max: 100 },
    yAxis: { type: "category", data: sorted.map((g) => g.name) },
    series: [
      {
        type: "bar",
        data: sorted.map((g) => g.rating_score ?? 0),
        itemStyle: { color: "#38bdf8" },
      },
    ],
  };
});
</script>

<template>
  <BaseChart :option="option" :empty="data.length === 0" />
</template>
