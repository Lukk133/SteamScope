<script setup lang="ts">
import { computed } from "vue";
import type { EChartsOption } from "echarts";
import BaseChart from "./BaseChart.vue";
import type { DeveloperRow } from "@/api/types";

const props = defineProps<{ data: DeveloperRow[] }>();

const option = computed<EChartsOption>(() => {
  const sorted = [...props.data].sort(
    (a, b) => (a.total_estimated_revenue_usd ?? 0) - (b.total_estimated_revenue_usd ?? 0),
  );
  return {
    tooltip: { trigger: "axis", valueFormatter: (v) => `$${Number(v).toLocaleString()}` },
    grid: { left: 160, right: 24, top: 16, bottom: 24 },
    xAxis: { type: "value" },
    yAxis: { type: "category", data: sorted.map((d) => d.developer) },
    series: [
      {
        type: "bar",
        data: sorted.map((d) => d.total_estimated_revenue_usd ?? 0),
        itemStyle: { color: "#34d399" },
      },
    ],
  };
});
</script>

<template>
  <BaseChart :option="option" :empty="data.length === 0" />
</template>
