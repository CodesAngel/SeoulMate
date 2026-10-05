import type {
  AccountProfileResponse,
  Drama,
  ProfileResponse,
  RatingEntry,
  RecommendationResponse,
  SearchFilters,
  WatchlistEntry,
  WatchStatus,
} from "@/lib/types";

export const MOCK_USER_ID = "7ad67681-f972-49f4-a695-2c0b20e14b9a";
export const MOCK_USER_EMAIL = "preview@seoulmate.local";
export const MOCK_USER_NAME = "SeoulMate Preview";

export const MOCK_DRAMAS: Drama[] = [
  {
    drama_id: 101,
    Title: "Crash Landing on You",
    Genre: "Romance, Comedy, Drama, Political",
    Description: "A South Korean heiress is swept across the border by a storm and meets a principled North Korean officer who decides to protect her.",
    Cast: "Hyun Bin, Son Ye Jin, Seo Ji Hye, Kim Jung Hyun",
    Director: "Lee Jung Hyo",
    Network: "tvN",
    "Release Years": "2019",
    "Also Known As": "Love's Emergency Landing",
    rating_value: 9.0,
    episodes: 16,
    keywords: "Star Crossed Lovers, Found Family, Military, Strong Female Lead, Secret Romance",
    watchers: 212400,
    poster_thumbnail_url: "/mock-posters/crash-landing.webp",
    poster_original_url: "/mock-posters/crash-landing.webp",
  },
  {
    drama_id: 102,
    Title: "Hospital Playlist",
    Genre: "Friendship, Romance, Life, Medical",
    Description: "Five doctors who have been friends since medical school share ordinary days, difficult choices, music, and meals at the same hospital.",
    Cast: "Jo Jung Suk, Yoo Yeon Seok, Jung Kyung Ho, Kim Dae Myung, Jeon Mi Do",
    Director: "Shin Won Ho",
    Network: "tvN",
    "Release Years": "2020",
    rating_value: 9.1,
    episodes: 12,
    keywords: "Found Family, Doctors, Band, Slice of Life, Longtime Friends",
    watchers: 118900,
    poster_thumbnail_url: "/mock-posters/hospital-playlist.webp",
    poster_original_url: "/mock-posters/hospital-playlist.webp",
  },
  {
    drama_id: 103,
    Title: "Business Proposal",
    Genre: "Comedy, Romance, Drama",
    Description: "An employee attends a blind date in place of her friend, only to discover that the man across the table is her company's CEO.",
    Cast: "Ahn Hyo Seop, Kim Se Jeong, Kim Min Gue, Seol In Ah",
    Director: "Park Seon Ho",
    Network: "SBS",
    "Release Years": "2022",
    rating_value: 8.7,
    episodes: 12,
    keywords: "Fake Dating, Office Romance, Hidden Identity, Friendship, Contract Relationship",
    watchers: 176300,
    poster_thumbnail_url: "/mock-posters/business-proposal.webp",
    poster_original_url: "/mock-posters/business-proposal.webp",
  },
  {
    drama_id: 104,
    Title: "Twenty-Five Twenty-One",
    Genre: "Romance, Life, Youth, Drama",
    Description: "A determined teenage fencer and a young man rebuilding his life meet during a time of uncertainty and grow together.",
    Cast: "Kim Tae Ri, Nam Joo Hyuk, Bona, Choi Hyun Wook, Lee Joo Myung",
    Director: "Jung Ji Hyun",
    Network: "tvN",
    "Release Years": "2022",
    rating_value: 8.8,
    episodes: 16,
    keywords: "Coming of Age, Fencing, Friendship, First Love, 1990s",
    watchers: 142700,
    poster_thumbnail_url: "/mock-posters/twenty-five-twenty-one.webp",
    poster_original_url: "/mock-posters/twenty-five-twenty-one.webp",
  },
  {
    drama_id: 105,
    Title: "Vincenzo",
    Genre: "Comedy, Law, Crime, Drama",
    Description: "A Korean-Italian mafia lawyer returns to Seoul and uses ruthless tactics to take on a corrupt conglomerate.",
    Cast: "Song Joong Ki, Jeon Yeo Been, Ok Taec Yeon, Kwak Dong Yeon",
    Director: "Kim Hee Won",
    Network: "tvN",
    "Release Years": "2021",
    rating_value: 8.9,
    episodes: 20,
    keywords: "Antihero, Revenge, Corruption, Found Family, Dark Comedy",
    watchers: 165800,
    poster_thumbnail_url: "/mock-posters/vincenzo.webp",
    poster_original_url: "/mock-posters/vincenzo.webp",
  },
  {
    drama_id: 106,
    Title: "Extraordinary Attorney Woo",
    Genre: "Law, Romance, Life, Drama",
    Description: "A brilliant rookie attorney on the autism spectrum approaches difficult cases with a unique perspective and an exceptional memory.",
    Cast: "Park Eun Bin, Kang Tae Oh, Kang Ki Young, Jeon Bae Soo",
    Director: "Yoo In Shik",
    Network: "ENA",
    "Release Years": "2022",
    rating_value: 9.0,
    episodes: 16,
    keywords: "Autism, Lawyer, Workplace, Legal Case, Personal Growth",
    watchers: 153600,
    poster_thumbnail_url: "/mock-posters/attorney-woo.webp",
    poster_original_url: "/mock-posters/attorney-woo.webp",
  },
  {
    drama_id: 107,
    Title: "Alchemy of Souls",
    Genre: "Action, Historical, Romance, Fantasy",
    Description: "In a kingdom shaped by magic, a powerful assassin trapped in another body becomes entangled with a noble heir seeking a new destiny.",
    Cast: "Lee Jae Wook, Jung So Min, Hwang Min Hyun, Shin Seung Ho",
    Director: "Park Joon Hwa",
    Network: "tvN",
    "Release Years": "2022",
    rating_value: 9.0,
    episodes: 20,
    keywords: "Magic, Body Swap, Master Student, Hidden Identity, Fantasy World",
    watchers: 138200,
    poster_thumbnail_url: "/mock-posters/alchemy-of-souls.webp",
    poster_original_url: "/mock-posters/alchemy-of-souls.webp",
  },
  {
    drama_id: 108,
    Title: "Moving",
    Genre: "Action, Thriller, Mystery, Supernatural",
    Description: "Teenagers hiding inherited abilities and their parents carrying painful secrets unite when a dangerous force begins hunting them.",
    Cast: "Ryu Seung Ryong, Han Hyo Joo, Jo In Sung, Lee Jung Ha, Go Youn Jung",
    Director: "Park In Je",
    Network: "Disney+",
    "Release Years": "2023",
    rating_value: 9.1,
    episodes: 20,
    keywords: "Superpowers, Family, Secret Agent, High School, Protective Parents",
    watchers: 94700,
    poster_thumbnail_url: "/mock-posters/moving.webp",
    poster_original_url: "/mock-posters/moving.webp",
  },
  {
    drama_id: 109,
    Title: "Lovely Runner",
    Genre: "Comedy, Romance, Youth, Fantasy",
    Description: "A devoted fan travels back in time and tries to rewrite the fate of the star whose music once gave her hope.",
    Cast: "Byeon Woo Seok, Kim Hye Yoon, Song Geon Hee, Lee Seung Hyub",
    Director: "Yoon Jong Ho",
    Network: "tvN",
    "Release Years": "2024",
    rating_value: 9.0,
    episodes: 16,
    keywords: "Time Travel, Idol, First Love, Fan, Second Chance",
    watchers: 126500,
    poster_thumbnail_url: "/mock-posters/lovely-runner.webp",
    poster_original_url: "/mock-posters/lovely-runner.webp",
  },
  {
    drama_id: 110,
    Title: "My Mister",
    Genre: "Psychological, Life, Drama, Family",
    Description: "Two exhausted people from different generations recognize each other's pain and slowly become a source of strength for one another.",
    Cast: "Lee Sun Kyun, IU, Park Ho San, Song Sae Byuk",
    Director: "Kim Won Suk",
    Network: "tvN",
    "Release Years": "2018",
    rating_value: 9.2,
    episodes: 16,
    keywords: "Healing, Workplace, Poverty, Family, Human Connection",
    watchers: 104300,
    poster_thumbnail_url: "/mock-posters/my-mister.webp",
    poster_original_url: "/mock-posters/my-mister.webp",
  },
];

const timestamp = "2026-10-06T10:00:00.000Z";
let mockWatchlist: WatchlistEntry[] = [
  { drama: MOCK_DRAMAS[1], status: "watching", created_at: timestamp, updated_at: timestamp },
  { drama: MOCK_DRAMAS[3], status: "completed", created_at: timestamp, updated_at: timestamp },
  { drama: MOCK_DRAMAS[6], status: "planned", created_at: timestamp, updated_at: timestamp },
  { drama: MOCK_DRAMAS[9], status: "completed", created_at: timestamp, updated_at: timestamp },
];
let mockRatings: RatingEntry[] = [
  { drama: MOCK_DRAMAS[3], rating: 9, created_at: timestamp, updated_at: timestamp },
  { drama: MOCK_DRAMAS[9], rating: 10, created_at: timestamp, updated_at: timestamp },
];
let mockDisplayName = MOCK_USER_NAME;
let mockAvatarPath: string | null = null;

function delay(signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    if (signal?.aborted) {
      reject(signal.reason);
      return;
    }
    const timeout = setTimeout(resolve, 180);
    signal?.addEventListener("abort", () => {
      clearTimeout(timeout);
      reject(signal.reason);
    }, { once: true });
  });
}

function dramaById(dramaId: number) {
  const drama = MOCK_DRAMAS.find((item) => item.drama_id === dramaId);
  if (!drama) throw new Error("Mock drama not found.");
  return drama;
}

function statistics() {
  const count = (status: WatchStatus) => mockWatchlist.filter((item) => item.status === status).length;
  const average = mockRatings.length
    ? Number((mockRatings.reduce((total, item) => total + item.rating, 0) / mockRatings.length).toFixed(1))
    : null;
  const planned = count("planned");
  const watching = count("watching");
  const completed = count("completed");
  const paused = count("paused");
  const dropped = count("dropped");
  return {
    saved_total: mockWatchlist.length,
    active_total: planned + watching + paused,
    planned,
    watching,
    completed,
    paused,
    dropped,
    ratings_total: mockRatings.length,
    average_rating: average,
  };
}

export async function mockSearch(filters: SearchFilters, signal?: AbortSignal): Promise<RecommendationResponse> {
  await delay(signal);
  const query = filters.query.trim().toLowerCase();
  const generic = !query || /recommend|something|dramas like/.test(query);
  let results = MOCK_DRAMAS.filter((drama) => {
    const haystack = [drama.Title, drama.Genre, drama.Description, drama.Cast, drama.keywords]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return generic || query.split(/\s+/).some((term) => term.length > 2 && haystack.includes(term));
  });
  if (filters.similarTo) results = results.filter((drama) => drama.Title !== filters.similarTo);
  if (filters.genre) results = results.filter((drama) => drama.Genre?.toLowerCase().includes(filters.genre!.toLowerCase()));
  if (filters.year) results = results.filter((drama) => drama["Release Years"]?.includes(filters.year!));
  if (filters.minRating) results = results.filter((drama) => Number(drama.rating_value) >= Number(filters.minRating));
  if (filters.sortBy === "rating_value") results.sort((a, b) => Number(b.rating_value) - Number(a.rating_value));
  if (filters.sortBy === "watchers") results.sort((a, b) => (b.watchers ?? 0) - (a.watchers ?? 0));
  if (filters.sortBy === "release_year") results.sort((a, b) => Number(b["Release Years"]) - Number(a["Release Years"]));
  return {
    query: { Title: filters.query, expanded: generic ? "character-driven stories, memorable relationships, acclaimed Korean dramas" : undefined },
    analysis: { intent: filters.similarTo ? "similar_drama" : "natural_language", confidence: 0.94 },
    recommendations: results.slice(0, filters.topN ?? 12),
    personalization: { applied: true, summary: "Preview recommendations shaped by your mock taste profile." },
    search_id: `mock-search-${Date.now()}`,
  };
}

export async function mockGetDrama(title: string, signal?: AbortSignal) {
  await delay(signal);
  const drama = MOCK_DRAMAS.find((item) => item.Title.toLowerCase() === title.toLowerCase());
  if (!drama) throw new Error(`No mock drama named “${title}” was found.`);
  return drama;
}

export async function mockGetProfile(userId: string, signal?: AbortSignal): Promise<ProfileResponse> {
  await delay(signal);
  const stats = statistics();
  return {
    user_id: userId,
    profile: {
      user_id: userId,
      created_at: "2026-01-12T09:30:00.000Z",
      last_updated: timestamp,
      preferences: {
        genres: { Romance: 0.94, Drama: 0.88, Fantasy: 0.76, Comedy: 0.69 },
        actors: { "Kim Tae Ri": 0.91, "Park Eun Bin": 0.84, IU: 0.81 },
        directors: { "Shin Won Ho": 0.9, "Kim Won Suk": 0.83 },
        themes: { "Found Family": 0.95, Healing: 0.89, "Strong Female Lead": 0.8 },
        publishers: { tvN: 0.92, SBS: 0.71 },
      },
      statistics: {
        total_interactions: 128,
        total_clicks: 74,
        total_watchlist_adds: stats.saved_total,
        total_watched: stats.completed,
        avg_rating: stats.average_rating ?? 0,
        total_ratings: stats.ratings_total,
        rating_style: "Enthusiastic",
      },
      viewing_patterns: {
        preferred_episode_count: 16,
        preferred_years: [2022, 2023, 2024],
        binge_watcher: true,
        rating_style: "Enthusiastic",
      },
      recent_interactions: mockRatings.map((item) => ({
        drama_title: item.drama.Title,
        interaction_type: "rating",
        timestamp: item.updated_at ?? timestamp,
        rating: item.rating,
      })),
      persona: "Emotion-led Story Explorer",
    },
    top_preferences: {
      genres: [["Romance", 0.94], ["Drama", 0.88], ["Fantasy", 0.76], ["Comedy", 0.69]],
      actors: [["Kim Tae Ri", 0.91], ["Park Eun Bin", 0.84], ["IU", 0.81]],
      directors: [["Shin Won Ho", 0.9], ["Kim Won Suk", 0.83]],
      themes: [["Found Family", 0.95], ["Healing", 0.89], ["Strong Female Lead", 0.8]],
    },
    persona: "Emotion-led Story Explorer",
    statistics: {
      total_interactions: 128,
      total_clicks: 74,
      total_watchlist_adds: stats.saved_total,
      total_watched: stats.completed,
      avg_rating: stats.average_rating ?? 0,
      total_ratings: stats.ratings_total,
      rating_style: "Enthusiastic",
    },
  };
}

export async function mockRateLegacy() {
  await delay();
  return { success: true, message: "Mock taste profile updated." };
}

export async function mockResetProfile() {
  await delay();
  return { success: true, message: "Mock taste profile reset for this preview." };
}

export async function mockGetAccount(signal?: AbortSignal): Promise<AccountProfileResponse> {
  await delay(signal);
  return {
    profile: {
      id: MOCK_USER_ID,
      display_name: mockDisplayName,
      avatar_path: mockAvatarPath,
      avatar_url: null,
      created_at: "2026-01-12T09:30:00.000Z",
      updated_at: new Date().toISOString(),
    },
    statistics: statistics(),
  };
}

export async function mockUpdateAccount(update: { display_name?: string; avatar_path?: string | null }) {
  await delay();
  if (update.display_name !== undefined) mockDisplayName = update.display_name;
  if (update.avatar_path !== undefined) mockAvatarPath = update.avatar_path;
  return mockGetAccount();
}

export async function mockDeleteAccount() {
  await delay();
  mockWatchlist = [];
  mockRatings = [];
  mockAvatarPath = null;
}

export async function mockGetWatchlist(signal?: AbortSignal) {
  await delay(signal);
  return { items: [...mockWatchlist] };
}

export async function mockMergeWatchlist(items: Array<{ drama_id: number; status: WatchStatus }>) {
  await delay();
  for (const item of items) {
    if (!mockWatchlist.some((entry) => entry.drama.drama_id === item.drama_id)) {
      mockWatchlist.unshift({ drama: dramaById(item.drama_id), status: item.status, created_at: timestamp, updated_at: timestamp });
    }
  }
  return { items: [...mockWatchlist] };
}

export async function mockSaveWatchlistItem(dramaId: number, status: WatchStatus) {
  await delay();
  const item = { drama: dramaById(dramaId), status, created_at: timestamp, updated_at: new Date().toISOString() };
  mockWatchlist = [item, ...mockWatchlist.filter((entry) => entry.drama.drama_id !== dramaId)];
  return { item };
}

export async function mockRemoveWatchlistItem(dramaId: number) {
  await delay();
  mockWatchlist = mockWatchlist.filter((entry) => entry.drama.drama_id !== dramaId);
}

export async function mockGetRatings(signal?: AbortSignal) {
  await delay(signal);
  return { items: [...mockRatings] };
}

export async function mockSaveRating(dramaId: number, rating: number) {
  await delay();
  const drama = dramaById(dramaId);
  const item: RatingEntry = { drama, rating, created_at: timestamp, updated_at: new Date().toISOString() };
  const watchlistItem: WatchlistEntry = { drama, status: "completed", created_at: timestamp, updated_at: new Date().toISOString() };
  mockRatings = [item, ...mockRatings.filter((entry) => entry.drama.drama_id !== dramaId)];
  mockWatchlist = [watchlistItem, ...mockWatchlist.filter((entry) => entry.drama.drama_id !== dramaId)];
  return { item, watchlist_item: watchlistItem };
}
