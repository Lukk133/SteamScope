<script setup lang="ts">
import { computed } from "vue";
import type { EChartsOption } from "echarts";
import BaseChart from "./BaseChart.vue";
import type { PriceRangeRow } from "@/api/types";

const props = defineProps<{ data: PriceRangeRow[] }>();

const option = computed<EChartsOption>(() => ({
  tooltip: { trigger: "item" },
  legend: { bottom: 0, textStyle: { color: "#cbd5e1" } },
  series: [
    {
      type: "pie",
      radius: ["40%", "70%"],
      data: props.data.map((p) => ({ name: p.price_range_label, value: p.games_count })),
    },
  ],
}));
</script>

<template>
  <BaseChart :option="option" :empty="data.length === 0" />
</template>
