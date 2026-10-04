"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import Link from "next/link";
import { useApp } from "@/components/app-provider";
import { useAuth } from "@/components/auth-provider";
import { getProfile, rateDrama, resetProfile, searchDramas } from "@/lib/api";

function PreferenceList({ title, items }: { title: string; items: [string, number][] }) {
  return <div className="preference-section"><h3>{title}</h3>{items.length ? items.slice(0, 7).map(([label, score]) => <div className="preference-row" key={label}><span>{label}</span><div className="preference-track"><div className="preference-fill" style={{ width: `${Math.max(4, Math.round(score * 100))}%` }} /></div><strong>{Math.round(score * 100)}%</strong></div>) : <p className="muted">Rate a few dramas to build this part of your profile.</p>}</div>;
}

export default function ProfilePage() {
  const { user } = useAuth();
  const { ready, userId, sessionId, ratingEntries, saveRating } = useApp();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [rating, setRating] = useState("9");
  const [message, setMessage] = useState("");
  const profile = useQuery({ queryKey: ["profile", userId], queryFn: ({ signal }) => getProfile(userId, signal), enabled: ready && Boolean(userId), retry: false });
  const rate = useMutation({ mutationFn: async () => {
    if (!user) throw new Error("Sign in to save ratings to your account.");
    const result = await searchDramas({ query: title.trim(), topN: 8, userId, sessionId });
    const normalizedTitle = title.trim().toLocaleLowerCase();
    const drama = result.recommendations.find((item) => item.Title.toLocaleLowerCase() === normalizedTitle) ?? result.recommendations[0];
    if (!drama?.drama_id) throw new Error("We could not find that drama. Try its exact title.");
    await saveRating(drama, Number(rating));
    await rateDrama(userId, drama.Title, Number(rating)).catch(() => undefined);
    return { message: `Rating saved: ${drama.Title} = ${rating}/10` };
  }, onSuccess: async (data) => { setMessage(data.message); setTitle(""); await queryClient.invalidateQueries({ queryKey: ["profile", userId] }); }, onError: (error) => setMessage(error instanceof Error ? error.message : "Could not save rating") });
  const reset = useMutation({ mutationFn: () => resetProfile(userId), onSuccess: async (data) => { setMessage(data.message); await queryClient.invalidateQueries({ queryKey: ["profile", userId] }); } });

  function submit(event: FormEvent) { event.preventDefault(); if (title.trim()) rate.mutate(); }
  const data = profile.data;
  const personas = Array.isArray(data?.persona) ? data.persona : data?.persona ? [data.persona] : ["Taste explorer"];
  const stats = data?.statistics || {};

  return (
    <>
      <section className="page-hero"><div className="shell"><span className="eyebrow">Personalized for you</span><h1 className="display">Your taste, taking shape</h1><p>Ratings and saved dramas teach SeoulMate which genres, actors, themes, and creators feel most like you.</p></div></section>
      <div className="shell profile-layout">
        <section className="profile-card">
          <h2>Your taste map</h2>
          {profile.isLoading && <div className="profile-loading"><span /><span /><span /></div>}
          {profile.isError && <div className="error-banner" role="alert">{profile.error instanceof Error ? profile.error.message : "Profile unavailable"} <button type="button" onClick={() => profile.refetch()}>Try again</button></div>}
          {!profile.isLoading && <>
            <PreferenceList title="Top genres" items={data?.top_preferences.genres || []} />
            <PreferenceList title="Favorite actors" items={data?.top_preferences.actors || []} />
            <PreferenceList title="Story themes" items={data?.top_preferences.themes || []} />
            <PreferenceList title="Directors" items={data?.top_preferences.directors || []} />
          </>}
        </section>
        <aside className="profile-sidebar">
          <div className="profile-card persona-card"><span className="eyebrow">Your current persona</span><h2>{personas[0]}</h2><p>This changes as you watch, save, and rate more stories.</p><div className="persona-list">{personas.map((persona) => <span key={persona}>{persona}</span>)}</div></div>
          <div className="profile-card" style={{ marginTop: 18 }}><h2>Teach SeoulMate</h2>{user ? <form className="rate-form" onSubmit={submit}><label className="field-label" htmlFor="profile-drama">Drama title</label><input id="profile-drama" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Hospital Playlist" /><label className="field-label" htmlFor="profile-rating">Your rating</label><select id="profile-rating" value={rating} onChange={(event) => setRating(event.target.value)}>{[10,9.5,9,8.5,8,7.5,7,6,5].map((score) => <option value={score} key={score}>{score}/10</option>)}</select><button className="primary-button" type="submit" disabled={rate.isPending}>{rate.isPending ? "Saving…" : "Save rating"}</button></form> : <p className="muted"><Link className="text-link" href="/auth/login">Sign in</Link> to build a persistent taste profile.</p>}{message && <p className="muted" role="status">{message}</p>}</div>
          <div className="profile-card" style={{ marginTop: 18 }}><h2>Your activity</h2><div className="stat-grid"><div className="stat-box"><strong>{ratingEntries.length}</strong><span>saved ratings</span></div>{Object.entries(stats).filter(([key]) => key !== "total_ratings").slice(0, 3).map(([key, value]) => <div className="stat-box" key={key}><strong>{String(value)}</strong><span>{key.replaceAll("_", " ")}</span></div>)}</div><button className="danger-button" onClick={() => { if (window.confirm("Reset everything SeoulMate has learned about your taste?")) reset.mutate(); }} disabled={reset.isPending}>{reset.isPending ? "Resetting…" : "Reset taste profile"}</button></div>
        </aside>
      </div>
    </>
  );
}
