import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import KpiCards from "./KpiCards.vue";
import type { Overview } from "@/api/types";

const sample: Overview = {
  total_games: 1234,
  total_developers: 56,
  total_genres: 12,
  avg_rating: 78.5,
  avg_price_usd: 14.99,
  total_estimated_owners: 5000000,
  total_reviews: 99999,
  total_estimated_revenue_usd: 12345678,
};

describe("KpiCards", () => {
  it("renderuje liczbę gier gdy overview podane", () => {
    const wrapper = mount(KpiCards, { props: { overview: sample } });
    expect(wrapper.text()).toContain("1");
    expect(wrapper.text()).toContain("Gry");
  });

  it("pokazuje stan pusty gdy overview = null", () => {
    const wrapper = mount(KpiCards, { props: { overview: null } });
    expect(wrapper.text()).toContain("Brak danych");
  });
});
