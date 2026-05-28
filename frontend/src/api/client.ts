import type {
  DeveloperRow,
  GameDetail,
  GenreStat,
  MonthlyReleaseRow,
  Overview,
  Paginated,
  PriceRangeRow,
  SentimentRow,
  TopRatedGame,
} from "./types";

const BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

type QueryValue = string | number | undefined | null;

function buildUrl(path: string, params?: Record<string, QueryValue>): string {
  const url = new URL(path, BASE_URL);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

async function get<T>(path: string, params?: Record<string, QueryValue>): Promise<T> {
  const res = await fetch(buildUrl(path, params));
  if (!res.ok) {
    throw new Error(`API ${path} → ${res.status}`);
  }
  return (await res.json()) as T;
}

export const api = {
  overview: () => get<Overview>("/api/overview"),
  topRatedGames: (params?: { limit?: number; offset?: number }) =>
    get<Paginated<TopRatedGame>>("/api/views/top-rated-games", params),
  genreStats: () => get<Paginated<GenreStat>>("/api/views/genre-stats"),
  developerLeaderboard: (params?: { limit?: number; offset?: number }) =>
    get<Paginated<DeveloperRow>>("/api/views/developer-leaderboard", params),
  priceRangeDistribution: () =>
    get<Paginated<PriceRangeRow>>("/api/views/price-range-distribution"),
  sentimentPerGenre: () => get<Paginated<SentimentRow>>("/api/views/sentiment-per-genre"),
  monthlyReleases: (params?: { year_from?: number; year_to?: number }) =>
    get<Paginated<MonthlyReleaseRow>>("/api/views/monthly-releases", params),
  games: (params?: { q?: string; limit?: number; offset?: number }) =>
    get<Paginated<GameDetail>>("/api/games", params),
  gameDetail: (gameId: number) => get<GameDetail>(`/api/games/${gameId}`),
};
