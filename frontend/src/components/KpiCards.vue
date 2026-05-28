<script setup lang="ts">
import { computed } from "vue";
import Card from "@/components/ui/Card.vue";
import type { Overview } from "@/api/types";

const props = defineProps<{ overview: Overview | null }>();

function fmt(value: number | null, opts?: Intl.NumberFormatOptions): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("pl-PL", opts).format(value);
}

const cards = computed(() => {
  if (!props.overview) return [];
  const o = props.overview;
  return [
    { label: "Gry", value: fmt(o.total_games) },
    { label: "Deweloperzy", value: fmt(o.total_developers) },
    { label: "Gatunki", value: fmt(o.total_genres) },
    { label: "Śr. ocena", value: o.avg_rating === null ? "—" : fmt(o.avg_rating, { maximumFractionDigits: 1 }) },
    { label: "Recenzje", value: fmt(o.total_reviews) },
    {
      label: "Szac. przychód",
      value: o.total_estimated_revenue_usd === null ? "—" : `$${fmt(o.total_estimated_revenue_usd, { maximumFractionDigits: 0 })}`,
    },
  ];
});
</script>

<template>
  <div v-if="cards.length" class="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
    <Card v-for="c in cards" :key="c.label">
      <div class="text-xs uppercase tracking-wide text-muted-foreground">{{ c.label }}</div>
      <div class="mt-1 text-2xl font-bold">{{ c.value }}</div>
    </Card>
  </div>
  <Card v-else>
    <div class="text-sm text-muted-foreground">Brak danych — uruchom pipeline ingestion/ETL.</div>
  </Card>
</template>
