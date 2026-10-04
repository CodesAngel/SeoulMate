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

export type UserStatistics = {
  total_interactions: number;
  total_clicks: number;
  total_watchlist_adds: number;
  total_watched: number;
  avg_rating: number;
  total_ratings: number;
  rating_style?: string;
};

export type UserProfile = {
  user_id: string;
  created_at: string;
  last_updated: string;
  preferences: {
    genres: Record<string, number>;
    actors: Record<string, number>;
    directors: Record<string, number>;
    themes: Record<string, number>;
    publishers: Record<string, number>;
  };
  statistics: UserStatistics;
  viewing_patterns: {
    preferred_episode_count: number | null;
    preferred_years: Array<string | number>;
    binge_watcher: boolean;
    rating_style: string;
  };
  recent_interactions: Array<{
    drama_title: string;
    interaction_type: string;
    timestamp: string;
    rating?: number;
  }>;
  persona?: string | string[];
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
  profile: UserProfile;
  top_preferences: {
    genres: [string, number][];
    actors: [string, number][];
    directors: [string, number][];
    themes: [string, number][];
  };
  persona: string | string[];
  statistics: UserStatistics;
};

export type InteractionType = "click" | "watchlist_add" | "watchlist_remove";
