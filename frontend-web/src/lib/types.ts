export type Drama = {
  Title: string;
  Genre?: string;
  Description?: string;
  Cast?: string;
  Director?: string;
  Network?: string;
  "Release Years"?: string;
  "Also Known As"?: string;
  rating_value?: string | number;
  episodes?: string | number;
  keywords?: string;
  Image?: string;
  image_url?: string;
  image_id?: string;
  watchers?: number;
  boost_multiplier?: number;
  boost_details?: Record<string, number>;
};

export type RecommendationResponse = {
  query: { Title: string; expanded?: string };
  analysis?: {
    intent?: string;
    dynamic_alpha?: number;
    confidence?: number;
  };
  recommendations: Drama[];
  personalization?: {
    applied?: boolean;
    summary?: string;
  };
  search_id?: string;
};

export type SearchFilters = {
  query: string;
  topN?: number;
  genre?: string;
  year?: string;
  minRating?: string;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
  similarTo?: string;
  refresh?: number;
  userId?: string;
  sessionId?: string;
};

export type ProfileResponse = {
  user_id: string;
  profile: Record<string, unknown>;
  top_preferences: {
    genres: [string, number][];
    actors: [string, number][];
    directors: [string, number][];
    themes: [string, number][];
  };
  persona: string | string[];
  statistics: Record<string, number>;
};

export type InteractionType = "click" | "watchlist_add" | "watchlist_remove";
