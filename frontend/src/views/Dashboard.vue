<script setup lang="ts">
import { onMounted } from "vue";
import { useDashboardStore } from "@/stores/dashboard";
import Card from "@/components/ui/Card.vue";
import KpiCards from "@/components/KpiCards.vue";
import GameSearch from "@/components/GameSearch.vue";
import GameDetailDrawer from "@/components/GameDetailDrawer.vue";
import MonthlyFilter from "@/components/MonthlyFilter.vue";
import TopRatedChart from "@/components/charts/TopRatedChart.vue";
import GenreStatsChart from "@/components/charts/GenreStatsChart.vue";
import DeveloperChart from "@/components/charts/DeveloperChart.vue";
import PriceRangeChart from "@/components/charts/PriceRangeChart.vue";
import SentimentChart from "@/components/charts/SentimentChart.vue";
import MonthlyReleasesChart from "@/components/charts/MonthlyReleasesChart.vue";

const store = useDashboardStore();

onMounted(() => store.loadAll());
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 py-6">
    <header class="mb-6">
      <h1 class="text-3xl font-bold tracking-tight">SteamScope</h1>
      <p class="text-sm text-muted-foreground">Eksploracja rynku gier Steam</p>
    </header>

    <div v-if="store.error" class="mb-4 rounded-md border border-border bg-card p-4 text-sm">
      Nie udało się połączyć z API ({{ store.error }}). Czy backend działa na
      <code>VITE_API_BASE_URL</code>?
    </div>

    <KpiCards :overview="store.overview" :loading="store.loading" />

    <div class="mt-6">
      <GameSearch />
    </div>

    <div class="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card title="Najwyżej oceniane gry">
        <TopRatedChart :data="store.topRated" :loading="store.loading" />
      </Card>
      <Card title="Statystyki gatunków">
        <GenreStatsChart :data="store.genreStats" :loading="store.loading" />
      </Card>
      <Card title="Liderzy deweloperów (przychód)">
        <DeveloperChart :data="store.developers" :loading="store.loading" />
      </Card>
      <Card title="Rozkład przedziałów cenowych">
        <PriceRangeChart :data="store.priceRanges" :loading="store.loading" />
      </Card>
      <Card title="Sentyment per gatunek">
        <SentimentChart :data="store.sentiment" :loading="store.loading" />
      </Card>
      <Card title="Premiery wg miesiąca">
        <MonthlyFilter @apply="(f, t) => store.loadMonthly(f, t)" />
        <MonthlyReleasesChart :data="store.monthly" :loading="store.loading" />
      </Card>
    </div>

    <GameDetailDrawer />
  </div>
</template>
