export type Drama = {
  drama_id?: number;
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
  image_id?: string;
  poster_original_path?: string;
  poster_thumbnail_path?: string;
  poster_original_url?: string;
  poster_thumbnail_url?: string;
  watchers?: number;
  boost_multiplier?: number;
  boost_details?: Record<string, number>;
};

export type WatchStatus =
  | "planned"
  | "watching"
  | "completed"
  | "paused"
  | "dropped";

export type WatchlistEntry = {
  drama: Drama;
  status: WatchStatus;
  created_at?: string;
  updated_at?: string;
};

export type RatingEntry = {
  drama: Drama;
  rating: number;
  created_at?: string;
  updated_at?: string;
};

export type AccountProfile = {
  id: string;
  display_name: string | null;
  avatar_path: string | null;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
};

export type AccountStatistics = {
  saved_total: number;
  active_total: number;
  planned: number;
  watching: number;
  completed: number;
  paused: number;
  dropped: number;
  ratings_total: number;
  average_rating: number | null;
};

export type AccountProfileResponse = {
  profile: AccountProfile;
  statistics: AccountStatistics;
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

export type PostType = "discussion" | "review" | "recommendation";

export type CommunityAuthor = {
  user_id: string;
  display_name: string;
  avatar_url: string | null;
};

export type CommunityDrama = {
  drama_id: number;
  title: string;
  poster_thumbnail_url: string | null;
  rating_value: number | null;
  year: string | null;
};

export type CommunityPost = {
  id: string;
  post_type: PostType;
  title: string;
  body: string;
  rating: number | null;
  contains_spoilers: boolean;
  created_at: string;
  updated_at: string;
  like_count: number;
  comment_count: number;
  author: CommunityAuthor;
  drama: CommunityDrama | null;
  is_liked_by_me?: boolean;
  is_author?: boolean;
};

export type CommunityComment = {
  id: string;
  post_id: string;
  body: string;
  contains_spoilers: boolean;
  created_at: string;
  updated_at: string;
  author: CommunityAuthor;
  is_author?: boolean;
};

export type TrendingCommunityPost = {
  id: string;
  title: string;
  short_title: string;
  post_type: PostType;
  contains_spoilers: boolean;
  like_count: number;
  comment_count: number;
  drama_id: number | null;
  drama_title: string | null;
  drama_poster_thumbnail_url: string | null;
  participant_avatars: string[];
};

export type CommunityPostsResponse = {
  posts: CommunityPost[];
  total: number;
  page: number;
  has_more: boolean;
};

export type CreatePostPayload = {
  post_type: PostType;
  title: string;
  body: string;
  drama_id?: number | null;
  rating?: number | null;
  contains_spoilers: boolean;
};

export type UpdatePostPayload = {
  post_type?: PostType;
  title?: string;
  body?: string;
  drama_id?: number | null;
  rating?: number | null;
  contains_spoilers?: boolean;
};

export type CreateCommentPayload = {
  body: string;
  contains_spoilers: boolean;
};

export type UpdateCommentPayload = {
  body?: string;
  contains_spoilers?: boolean;
};

