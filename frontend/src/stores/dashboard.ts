import { defineStore } from "pinia";
import { ref } from "vue";
import { api } from "@/api/client";
import type {
  DeveloperRow,
  GenreStat,
  MonthlyReleaseRow,
  Overview,
  PriceRangeRow,
  SentimentRow,
  TopRatedGame,
} from "@/api/types";

export const useDashboardStore = defineStore("dashboard", () => {
  const overview = ref<Overview | null>(null);
  const topRated = ref<TopRatedGame[]>([]);
  const genreStats = ref<GenreStat[]>([]);
  const developers = ref<DeveloperRow[]>([]);
  const priceRanges = ref<PriceRangeRow[]>([]);
  const sentiment = ref<SentimentRow[]>([]);
  const monthly = ref<MonthlyReleaseRow[]>([]);

  const loading = ref(false);
  const error = ref<string | null>(null);

  async function loadAll(): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      const [ov, tr, gs, dev, pr, se, mo] = await Promise.all([
        api.overview(),
        api.topRatedGames({ limit: 15 }),
        api.genreStats(),
        api.developerLeaderboard({ limit: 15 }),
        api.priceRangeDistribution(),
        api.sentimentPerGenre(),
        api.monthlyReleases(),
      ]);
      overview.value = ov;
      topRated.value = tr.items;
      genreStats.value = gs.items;
      developers.value = dev.items;
      priceRanges.value = pr.items;
      sentiment.value = se.items;
      monthly.value = mo.items;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Błąd ładowania danych";
    } finally {
      loading.value = false;
    }
  }

  async function loadMonthly(yearFrom?: number, yearTo?: number): Promise<void> {
    const res = await api.monthlyReleases({ year_from: yearFrom, year_to: yearTo });
    monthly.value = res.items;
  }

  return {
    overview,
    topRated,
    genreStats,
    developers,
    priceRanges,
    sentiment,
    monthly,
    loading,
    error,
    loadAll,
    loadMonthly,
  };
});
