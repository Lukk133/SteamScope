<script setup lang="ts">
import { watch } from "vue";
import Card from "@/components/ui/Card.vue";
import Input from "@/components/ui/Input.vue";
import { useGamesStore } from "@/stores/games";

const store = useGamesStore();

// Debounce: każda zmiana inputa wyzwala search po 300 ms ciszy.
// Niezależne od Enter/submit — działa nawet jeśli fallthrough na komponent
// gubi zdarzenie keyboardowe.
let timer: ReturnType<typeof setTimeout> | null = null;
watch(
  () => store.query,
  () => {
    if (timer !== null) clearTimeout(timer);
    timer = setTimeout(() => {
      void store.search();
    }, 300);
  },
);
</script>

<template>
  <Card title="Wyszukiwarka gier">
    <!-- Natywny <form>: Enter w polu wyzwala submit standardowo, bez polegania
         na fallthrough modyfikatorów .enter przez komponent Vue (które nie
         przechodzą — modyfikatory klawiszowe działają tylko na DOM). -->
    <form class="flex gap-2" @submit.prevent="store.search()">
      <Input
        v-model="store.query"
        placeholder="Wpisz nazwę gry…"
        class="flex-1"
      />
      <button
        type="submit"
        class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
      >
        Szukaj
      </button>
    </form>
    <div v-if="store.searching" class="mt-3 text-sm text-muted-foreground">Szukam…</div>
    <ul v-else-if="store.results.length" class="mt-3 divide-y divide-border">
      <li
        v-for="g in store.results"
        :key="g.game_id"
        class="flex cursor-pointer items-center justify-between py-2 hover:text-primary"
        @click="store.openGame(g.game_id)"
      >
        <span>{{ g.name }}</span>
        <span class="text-sm text-muted-foreground">
          {{ g.rating_score === null ? "—" : Math.round(g.rating_score) }}
        </span>
      </li>
    </ul>
    <div v-else-if="store.query.trim()" class="mt-3 text-sm text-muted-foreground">
      Brak wyników.
    </div>
  </Card>
</template>
