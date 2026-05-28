export interface Overview {
  total_games: number;
  total_developers: number;
  total_genres: number;
  avg_rating: number | null;
  avg_price_usd: number | null;
  total_estimated_owners: number | null;
  total_reviews: number | null;
  total_estimated_revenue_usd: number | null;
}

export interface Paginated<T> {
  items: T[];
  total: number;
}

export interface TopRatedGame {
  game_id: number;
  name: string;
  genre: string | null;
  developer: string | null;
  price_usd: number | null;
  rating_score: number | null;
  review_count: number | null;
  estimated_owners: number | null;
}

export interface GenreStat {
  genre: string;
  games_count: number;
  avg_rating: number | null;
  avg_price_usd: number | null;
  avg_estimated_owners: number | null;
  total_review_count: number | null;
}

export interface DeveloperRow {
  developer: string;
  developer_class: string;
  games_count: number;
  avg_rating: number | null;
  total_estimated_revenue_usd: number | null;
  total_estimated_owners: number | null;
}

export interface PriceRangeRow {
  price_range_label: string;
  min_price: number;
  max_price: number | null;
  games_count: number;
  avg_rating: number | null;
}

export interface SentimentRow {
  genre: string;
  sentiment_label: string;
  games_count: number;
}

export interface MonthlyReleaseRow {
  year: number;
  month: number;
  month_name: string;
  season: string;
  games_count: number;
  avg_rating: number | null;
}

export interface GameDetail {
  game_id: number;
  name: string;
  genre: string | null;
  developer: string | null;
  developer_class: string | null;
  price_range_label: string | null;
  release_year: number | null;
  release_month: number | null;
  release_month_name: string | null;
  season: string | null;
  sentiment_label: string | null;
  price_usd: number | null;
  rating_score: number | null;
  review_count: number | null;
  positive_review_count: number | null;
  negative_review_count: number | null;
  estimated_owners: number | null;
  estimated_revenue_usd: number | null;
  release_date: string | null;
  playtime_avg_hours: number | null;
}
