<script setup lang="ts">
import { computed } from "vue";
import { useGamesStore } from "@/stores/games";

const store = useGamesStore();
const g = computed(() => store.selected);

function fmt(v: number | null | undefined, prefix = ""): string {
  if (v === null || v === undefined) return "—";
  return prefix + new Intl.NumberFormat("pl-PL").format(v);
}
</script>

<template>
  <div
    v-if="store.drawerOpen"
    class="fixed inset-0 z-50 flex justify-end bg-black/50"
    @click.self="store.closeDrawer()"
  >
    <aside class="h-full w-full max-w-md overflow-y-auto border-l border-border bg-card p-6">
      <div class="flex items-start justify-between">
        <h2 class="text-xl font-bold">{{ g?.name }}</h2>
        <button class="text-muted-foreground hover:text-foreground" @click="store.closeDrawer()">
          ✕
        </button>
      </div>
      <dl v-if="g" class="mt-4 space-y-2 text-sm">
        <div class="flex justify-between"><dt class="text-muted-foreground">Gatunek</dt><dd>{{ g.genre ?? "—" }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Deweloper</dt><dd>{{ g.developer ?? "—" }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Klasa</dt><dd>{{ g.developer_class ?? "—" }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Cena</dt><dd>{{ fmt(g.price_usd, "$") }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Ocena</dt><dd>{{ fmt(g.rating_score) }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Recenzje</dt><dd>{{ fmt(g.review_count) }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Pozytywne</dt><dd>{{ fmt(g.positive_review_count) }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Negatywne</dt><dd>{{ fmt(g.negative_review_count) }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Wł. (szac.)</dt><dd>{{ fmt(g.estimated_owners) }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Przychód (szac.)</dt><dd>{{ fmt(g.estimated_revenue_usd, "$") }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Premiera</dt><dd>{{ g.release_date ?? "—" }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Sentyment</dt><dd>{{ g.sentiment_label ?? "—" }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Śr. czas gry (h)</dt><dd>{{ fmt(g.playtime_avg_hours) }}</dd></div>
      </dl>
    </aside>
  </div>
</template>
