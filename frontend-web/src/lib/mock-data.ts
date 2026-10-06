import type {
  AccountProfileResponse,
  CommunityComment,
  CommunityPost,
  CommunityPostsResponse,
  CreateCommentPayload,
  CreatePostPayload,
  Drama,
  PostType,
  ProfileResponse,
  RatingEntry,
  RecommendationResponse,
  SearchFilters,
  TrendingCommunityPost,
  UpdateCommentPayload,
  UpdatePostPayload,
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

// ==========================================
// MOCK COMMUNITY STATE & APIS
// ==========================================

export let mockCommunityPosts: CommunityPost[] = [
  {
    id: "post-1",
    post_type: "discussion",
    title: "What did you think of the ending?",
    body: "I just finished the finale and I have so many mixed feelings! The chemistry between the leads throughout the entire journey was top tier, but that resolution in Switzerland felt like they had to rush through 3 episodes worth of emotional payoff into 20 minutes. What did everyone else think?",
    rating: null,
    contains_spoilers: false,
    created_at: new Date(Date.now() - 3 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 3 * 86400000).toISOString(),
    like_count: 890,
    comment_count: 1240,
    author: {
      user_id: "user-mina",
      display_name: "mina_joy",
      avatar_url: null,
    },
    drama: {
      drama_id: 101,
      title: "Crash Landing on You",
      poster_thumbnail_url: "/mock-posters/crash-landing.webp",
      rating_value: 9.0,
      year: "2019",
    },
  },
  {
    id: "post-2",
    post_type: "discussion",
    title: "Best second lead ever?",
    body: "We all have that one second lead that completely shattered our hearts into pieces. The quiet devotion, the constant loyalty, never asking for anything in return... he deserved the world. The writing gave him so much depth.",
    rating: null,
    contains_spoilers: false,
    created_at: new Date(Date.now() - 3 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 3 * 86400000).toISOString(),
    like_count: 892,
    comment_count: 450,
    author: {
      user_id: "user-seojun",
      display_name: "seojunwrites",
      avatar_url: null,
    },
    drama: {
      drama_id: 105,
      title: "Vincenzo",
      poster_thumbnail_url: "/mock-posters/vincenzo.webp",
      rating_value: 8.9,
      year: "2021",
    },
  },
  {
    id: "post-3",
    post_type: "discussion",
    title: "This scene lives in my head",
    body: "The cinematography in this episode was absolutely stunning. Every frame felt like a painting, K-dramas really do hit different. 🌙 Can we talk about this character development? From cold and guarded to someone who chooses vulnerability... I'm sobbing.",
    rating: null,
    contains_spoilers: false,
    created_at: new Date(Date.now() - 4 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 4 * 86400000).toISOString(),
    like_count: 640,
    comment_count: 310,
    author: {
      user_id: "user-hyejin",
      display_name: "hyejinflix",
      avatar_url: null,
    },
    drama: {
      drama_id: 104,
      title: "Twenty-Five Twenty-One",
      poster_thumbnail_url: "/mock-posters/twenty-five-twenty-one.webp",
      rating_value: 8.8,
      year: "2022",
    },
  },
  {
    id: "post-4",
    post_type: "recommendation",
    title: "Healing dramas for a rough week",
    body: "This drama gave me exactly what I needed right now. The characters feel so real and the found family dynamic is everything. 💛 If life has been heavy, five doctor friends eating meals together and practicing band in the basement will heal your soul.",
    rating: null,
    contains_spoilers: false,
    created_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    like_count: 1105,
    comment_count: 1420,
    author: {
      user_id: "user-chloe",
      display_name: "chloe_kdrama",
      avatar_url: null,
    },
    drama: {
      drama_id: 102,
      title: "Hospital Playlist",
      poster_thumbnail_url: "/mock-posters/hospital-playlist.webp",
      rating_value: 9.1,
      year: "2020",
    },
  },
  {
    id: "post-5",
    post_type: "review",
    title: "A Masterpiece in Subtle Heartbreak: My Mister",
    body: "My Mister is not an easy watch, but it is one of the most rewarding pieces of storytelling ever crafted. IU and Lee Sun-kyun deliver career-defining performances. It is a story of two deeply wounded souls finding dignity and mutual solace in an unforgiving world.",
    rating: 9.8,
    contains_spoilers: false,
    created_at: new Date(Date.now() - 5 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 5 * 86400000).toISOString(),
    like_count: 475,
    comment_count: 98,
    author: {
      user_id: "user-minjae",
      display_name: "cinephile_kim",
      avatar_url: null,
    },
    drama: {
      drama_id: 106,
      title: "My Mister",
      poster_thumbnail_url: "/mock-posters/my-mister.webp",
      rating_value: 9.2,
      year: "2018",
    },
  },
  {
    id: "post-6",
    post_type: "review",
    title: "EPISODE 16 TWIST: Let's unpack the courtroom revelation!",
    body: "SPOILER WARNING: The way the climax played out in the courtroom had my jaw on the floor. When the lighter clicked and the entire scheme was revealed, it cemented this as one of the best anti-hero sagas. The moral ambiguity made every victory feel dangerous.",
    rating: 9.2,
    contains_spoilers: true,
    created_at: new Date(Date.now() - 1 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 1 * 86400000).toISOString(),
    like_count: 512,
    comment_count: 141,
    author: {
      user_id: "user-alex",
      display_name: "dark_thriller_fan",
      avatar_url: null,
    },
    drama: {
      drama_id: 105,
      title: "Vincenzo",
      poster_thumbnail_url: "/mock-posters/vincenzo.webp",
      rating_value: 8.9,
      year: "2021",
    },
  },
  {
    id: "post-7",
    post_type: "discussion",
    title: "Which drama OST still gives you chills years later?",
    body: "Round and Round from Goblin, Stay With Me by Chanyeol & Punch, or Reset from School 2015? An iconic soundtrack can elevate a good drama into legendary territory. Tell me your undisputed #1 OST track!",
    rating: null,
    contains_spoilers: false,
    created_at: new Date(Date.now() - 6 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 6 * 86400000).toISOString(),
    like_count: 384,
    comment_count: 215,
    author: {
      user_id: "user-yuna",
      display_name: "soundtrack_junkie",
      avatar_url: null,
    },
    drama: {
      drama_id: 107,
      title: "Goblin",
      poster_thumbnail_url: "/mock-posters/goblin.webp",
      rating_value: 8.9,
      year: "2016",
    },
  },
  {
    id: "post-8",
    post_type: "discussion",
    title: "Twenty-Five Twenty-One Finale: Heartbreak or Realism?",
    body: "MAJOR SPOILERS: Did anyone else cry for three days after the final phone booth scene? While it broke my heart, I also appreciate how honest it was about first love in your youth versus the reality of growing up and drifting into adulthood.",
    rating: null,
    contains_spoilers: true,
    created_at: new Date(Date.now() - 5 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 5 * 86400000).toISOString(),
    like_count: 620,
    comment_count: 412,
    author: {
      user_id: "user-eunji",
      display_name: "nostalgia_nights",
      avatar_url: null,
    },
    drama: {
      drama_id: 104,
      title: "Twenty-Five Twenty-One",
      poster_thumbnail_url: "/mock-posters/twenty-five-twenty-one.webp",
      rating_value: 8.8,
      year: "2022",
    },
  },
];

export const mockCommunityComments: Record<string, CommunityComment[]> = {
  "post-1": [
    {
      id: "comment-101",
      post_id: "post-1",
      body: "I completely agree! They spent 15 episodes building tension and only gave us a few moments together at the end. Still an all-time favorite though.",
      contains_spoilers: false,
      created_at: new Date(Date.now() - 2.8 * 86400000).toISOString(),
      updated_at: new Date(Date.now() - 2.8 * 86400000).toISOString(),
      author: {
        user_id: "user-reader1",
        display_name: "kdrama_addict_99",
        avatar_url: null,
      },
    },
    {
      id: "comment-102",
      post_id: "post-1",
      body: "SPOILER: Honestly I was more devastated by Dan and Seung-jun's ending. That broke me way more than the main couple!",
      contains_spoilers: true,
      created_at: new Date(Date.now() - 2.5 * 86400000).toISOString(),
      updated_at: new Date(Date.now() - 2.5 * 86400000).toISOString(),
      author: {
        user_id: "user-reader2",
        display_name: "soju_and_tears",
        avatar_url: null,
      },
    },
  ],
  "post-2": [
    {
      id: "comment-201",
      post_id: "post-2",
      body: "Han Ji-pyeong was the real main character of our hearts! Even the grandmother cried with him.",
      contains_spoilers: false,
      created_at: new Date(Date.now() - 2.7 * 86400000).toISOString(),
      updated_at: new Date(Date.now() - 2.7 * 86400000).toISOString(),
      author: {
        user_id: "user-reader3",
        display_name: "start_up_survivor",
        avatar_url: null,
      },
    },
  ],
  "post-4": [
    {
      id: "comment-401",
      post_id: "post-4",
      body: "The band songs alone kept me going during exam week. Canon Rock was iconic!",
      contains_spoilers: false,
      created_at: new Date(Date.now() - 1.8 * 86400000).toISOString(),
      updated_at: new Date(Date.now() - 1.8 * 86400000).toISOString(),
      author: {
        user_id: "user-reader4",
        display_name: "comfort_vibes",
        avatar_url: null,
      },
    },
  ],
};

export const mockUserLikes = new Set<string>(["post-1", "post-4"]);

export async function mockGetCommunityPosts(
  filters?: {
    page?: number;
    limit?: number;
    post_type?: PostType;
    search?: string;
    drama_id?: number;
    sort?: "trending" | "recent";
  },
  userId?: string,
  signal?: AbortSignal,
): Promise<CommunityPostsResponse> {
  await delay(signal);
  const page = filters?.page || 1;
  const limit = filters?.limit || 10;
  const search = filters?.search?.trim().toLowerCase();
  const post_type = filters?.post_type;
  const drama_id = filters?.drama_id;
  const sort = filters?.sort || "trending";

  let filtered = [...mockCommunityPosts];

  if (post_type) {
    filtered = filtered.filter((p) => p.post_type === post_type);
  }
  if (drama_id) {
    filtered = filtered.filter((p) => p.drama?.drama_id === drama_id);
  }
  if (search) {
    filtered = filtered.filter(
      (p) =>
        p.title.toLowerCase().includes(search) ||
        p.body.toLowerCase().includes(search) ||
        (p.drama?.title && p.drama.title.toLowerCase().includes(search)),
    );
  }

  if (sort === "recent") {
    filtered.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  } else {
    // Trending sort: likes + comments * 2 + recency
    filtered.sort((a, b) => {
      const scoreA = a.like_count + a.comment_count * 2;
      const scoreB = b.like_count + b.comment_count * 2;
      return scoreB - scoreA;
    });
  }

  const total = filtered.length;
  const start = (page - 1) * limit;
  const paged = filtered.slice(start, start + limit).map((p) => ({
    ...p,
    is_liked_by_me: mockUserLikes.has(p.id),
    is_author: Boolean(userId && p.author.user_id === userId),
  }));

  return {
    posts: paged,
    total,
    page,
    has_more: start + limit < total,
  };
}

export async function mockGetCommunityTrending(signal?: AbortSignal): Promise<TrendingCommunityPost[]> {
  await delay(signal);
  // Exactly 4 items for the homepage trending strip
  return mockCommunityPosts.slice(0, 4).map((p) => ({
    id: p.id,
    title: p.title,
    short_title: p.title.length > 45 ? `${p.title.slice(0, 45)}…` : p.title,
    post_type: p.post_type,
    contains_spoilers: p.contains_spoilers,
    like_count: p.like_count,
    comment_count: p.comment_count,
    drama_id: p.drama?.drama_id ?? null,
    drama_title: p.drama?.title ?? null,
    drama_poster_thumbnail_url: p.drama?.poster_thumbnail_url ?? null,
    participant_avatars: ["/mock-posters/crash-landing.webp", "/mock-posters/hospital-playlist.webp", "/mock-posters/twenty-five-twenty-one.webp"],
  }));
}

export async function mockGetHomepageCommunity(signal?: AbortSignal): Promise<CommunityPost[]> {
  await delay(signal);
  // Return the 3 homepage community discussion cards matching the mockup
  return [mockCommunityPosts[3], mockCommunityPosts[1], mockCommunityPosts[0]].map((p) => ({
    ...p,
    is_liked_by_me: mockUserLikes.has(p.id),
  }));
}

export async function mockGetCommunityPost(postId: string, userId?: string, signal?: AbortSignal): Promise<CommunityPost> {
  await delay(signal);
  const post = mockCommunityPosts.find((p) => p.id === postId);
  if (!post) throw new Error("Community post not found");
  return {
    ...post,
    is_liked_by_me: mockUserLikes.has(post.id),
    is_author: Boolean(userId && post.author.user_id === userId),
  };
}

export async function mockCreateCommunityPost(payload: CreatePostPayload, userId: string): Promise<CommunityPost> {
  await delay();
  const drama = payload.drama_id ? dramaById(payload.drama_id) : null;
  const newPost: CommunityPost = {
    id: `post-${Date.now()}`,
    post_type: payload.post_type,
    title: payload.title,
    body: payload.body,
    rating: payload.rating ?? null,
    contains_spoilers: payload.contains_spoilers,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    like_count: 0,
    comment_count: 0,
    author: {
      user_id: userId,
      display_name: mockDisplayName || MOCK_USER_NAME,
      avatar_url: mockAvatarPath,
    },
    drama: drama
      ? {
          drama_id: drama.drama_id!,
          title: drama.Title,
          poster_thumbnail_url: drama.poster_thumbnail_url ?? null,
          rating_value: typeof drama.rating_value === "number" ? drama.rating_value : null,
          year: drama["Release Years"] ?? null,
        }
      : null,
    is_liked_by_me: false,
    is_author: true,
  };
  mockCommunityPosts.unshift(newPost);
  return newPost;
}

export async function mockUpdateCommunityPost(postId: string, payload: UpdatePostPayload, userId: string): Promise<CommunityPost> {
  await delay();
  const postIndex = mockCommunityPosts.findIndex((p) => p.id === postId);
  if (postIndex === -1) throw new Error("Community post not found");
  const existing = mockCommunityPosts[postIndex];
  if (existing.author.user_id !== userId) throw new Error("You can only edit your own posts");

  let updatedDrama = existing.drama;
  if (payload.drama_id !== undefined) {
    if (payload.drama_id === null) {
      updatedDrama = null;
    } else {
      const d = dramaById(payload.drama_id);
      updatedDrama = {
        drama_id: d.drama_id!,
        title: d.Title,
        poster_thumbnail_url: d.poster_thumbnail_url ?? null,
        rating_value: typeof d.rating_value === "number" ? d.rating_value : null,
        year: d["Release Years"] ?? null,
      };
    }
  }

  const updated: CommunityPost = {
    ...existing,
    post_type: payload.post_type ?? existing.post_type,
    title: payload.title ?? existing.title,
    body: payload.body ?? existing.body,
    rating: payload.rating !== undefined ? payload.rating : existing.rating,
    contains_spoilers: payload.contains_spoilers !== undefined ? payload.contains_spoilers : existing.contains_spoilers,
    drama: updatedDrama,
    updated_at: new Date().toISOString(),
    is_author: true,
  };
  mockCommunityPosts[postIndex] = updated;
  return updated;
}

export async function mockDeleteCommunityPost(postId: string, userId: string): Promise<void> {
  await delay();
  const existing = mockCommunityPosts.find((p) => p.id === postId);
  if (!existing) throw new Error("Community post not found");
  if (existing.author.user_id !== userId) throw new Error("You can only delete your own posts");
  mockCommunityPosts = mockCommunityPosts.filter((p) => p.id !== postId);
  delete mockCommunityComments[postId];
  mockUserLikes.delete(postId);
}

export async function mockGetCommunityComments(postId: string, userId?: string, signal?: AbortSignal): Promise<CommunityComment[]> {
  await delay(signal);
  const list = mockCommunityComments[postId] || [];
  return list.map((c) => ({
    ...c,
    is_author: Boolean(userId && c.author.user_id === userId),
  }));
}

export async function mockCreateCommunityComment(postId: string, payload: CreateCommentPayload, userId: string): Promise<CommunityComment> {
  await delay();
  const post = mockCommunityPosts.find((p) => p.id === postId);
  if (!post) throw new Error("Community post not found");

  const newComment: CommunityComment = {
    id: `comment-${Date.now()}`,
    post_id: postId,
    body: payload.body,
    contains_spoilers: payload.contains_spoilers,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    author: {
      user_id: userId,
      display_name: mockDisplayName || MOCK_USER_NAME,
      avatar_url: mockAvatarPath,
    },
    is_author: true,
  };

  if (!mockCommunityComments[postId]) {
    mockCommunityComments[postId] = [];
  }
  mockCommunityComments[postId].push(newComment);
  post.comment_count += 1;
  return newComment;
}

export async function mockUpdateCommunityComment(commentId: string, payload: UpdateCommentPayload, userId: string): Promise<CommunityComment> {
  await delay();
  for (const list of Object.values(mockCommunityComments)) {
    const idx = list.findIndex((c) => c.id === commentId);
    if (idx !== -1) {
      const target = list[idx];
      if (target.author.user_id !== userId) throw new Error("You can only edit your own comments");
      const updated: CommunityComment = {
        ...target,
        body: payload.body ?? target.body,
        contains_spoilers: payload.contains_spoilers !== undefined ? payload.contains_spoilers : target.contains_spoilers,
        updated_at: new Date().toISOString(),
        is_author: true,
      };
      list[idx] = updated;
      return updated;
    }
  }
  throw new Error("Comment not found");
}

export async function mockDeleteCommunityComment(commentId: string, userId: string): Promise<void> {
  await delay();
  for (const [postId, list] of Object.entries(mockCommunityComments)) {
    const target = list.find((c) => c.id === commentId);
    if (target) {
      if (target.author.user_id !== userId) throw new Error("You can only delete your own comments");
      mockCommunityComments[postId] = list.filter((c) => c.id !== commentId);
      const post = mockCommunityPosts.find((p) => p.id === postId);
      if (post && post.comment_count > 0) post.comment_count -= 1;
      return;
    }
  }
  throw new Error("Comment not found");
}

export async function mockLikeCommunityPost(postId: string): Promise<{ success: boolean; liked: boolean; like_count: number }> {
  await delay();
  const post = mockCommunityPosts.find((p) => p.id === postId);
  if (!post) throw new Error("Community post not found");
  if (!mockUserLikes.has(postId)) {
    mockUserLikes.add(postId);
    post.like_count += 1;
  }
  return { success: true, liked: true, like_count: post.like_count };
}

export async function mockUnlikeCommunityPost(postId: string): Promise<{ success: boolean; liked: boolean; like_count: number }> {
  await delay();
  const post = mockCommunityPosts.find((p) => p.id === postId);
  if (!post) throw new Error("Community post not found");
  if (mockUserLikes.has(postId)) {
    mockUserLikes.delete(postId);
    post.like_count = Math.max(0, post.like_count - 1);
  }
  return { success: true, liked: false, like_count: post.like_count };
}

