import { defineStore } from "pinia";
import { ref } from "vue";
import { api } from "@/api/client";
import type { GameDetail } from "@/api/types";

export const useGamesStore = defineStore("games", () => {
  const query = ref("");
  const results = ref<GameDetail[]>([]);
  const searching = ref(false);
  const selected = ref<GameDetail | null>(null);
  const drawerOpen = ref(false);

  async function search(): Promise<void> {
    const q = query.value.trim();
    if (!q) {
      results.value = [];
      return;
    }
    searching.value = true;
    try {
      const res = await api.games({ q, limit: 20 });
      results.value = res.items;
    } finally {
      searching.value = false;
    }
  }

  async function openGame(gameId: number): Promise<void> {
    selected.value = await api.gameDetail(gameId);
    drawerOpen.value = true;
  }

  function closeDrawer(): void {
    drawerOpen.value = false;
  }

  return { query, results, searching, selected, drawerOpen, search, openGame, closeDrawer };
});
