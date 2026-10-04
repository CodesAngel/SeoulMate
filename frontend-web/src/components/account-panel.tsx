"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { Activity, KeyRound, LogOut, Trash2, UserRound } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import {
  deleteMyAccount,
  getMyAccountProfile,
  updateMyAccountProfile,
} from "@/lib/api";
import type { AccountProfileResponse } from "@/lib/types";

const ALLOWED_AVATAR_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_AVATAR_SIZE = 2 * 1024 * 1024;

function readableError(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function AccountPanel({
  email,
  displayName: initialDisplayName,
}: {
  email: string;
  displayName: string;
}) {
  const router = useRouter();
  const { user, supabase, signOut, getAccessToken } = useAuth();
  const [account, setAccount] = useState<AccountProfileResponse | null>(null);
  const [displayName, setDisplayName] = useState(initialDisplayName);
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState("");
  const [loading, setLoading] = useState(true);
  const [profilePending, setProfilePending] = useState(false);
  const [profileMessage, setProfileMessage] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordPending, setPasswordPending] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState("");
  const [logoutPending, setLogoutPending] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [deletePending, setDeletePending] = useState(false);
  const [deleteMessage, setDeleteMessage] = useState("");

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    void (async () => {
      try {
        const accessToken = await getAccessToken();
        if (!accessToken) throw new Error("Your session has expired. Please sign in again.");
        const response = await getMyAccountProfile(accessToken, controller.signal);
        if (!active) return;
        setAccount(response);
        setDisplayName(response.profile.display_name || initialDisplayName);
      } catch (error) {
        if (active && !controller.signal.aborted) {
          setProfileMessage(readableError(error, "Could not load your account."));
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
      controller.abort();
    };
  }, [getAccessToken, initialDisplayName]);

  useEffect(() => {
    return () => {
      if (avatarPreview) URL.revokeObjectURL(avatarPreview);
    };
  }, [avatarPreview]);

  function selectAvatar(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setProfileMessage("");
    if (!file) {
      setAvatarFile(null);
      setAvatarPreview("");
      return;
    }
    if (!ALLOWED_AVATAR_TYPES.includes(file.type)) {
      setAvatarFile(null);
      setAvatarPreview("");
      setProfileMessage("Choose a JPEG, PNG, or WebP image.");
      event.target.value = "";
      return;
    }
    if (file.size > MAX_AVATAR_SIZE) {
      setAvatarFile(null);
      setAvatarPreview("");
      setProfileMessage("Avatar images must be 2 MB or smaller.");
      event.target.value = "";
      return;
    }
    setAvatarFile(file);
    setAvatarPreview(URL.createObjectURL(file));
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!user) return;
    const cleanedName = displayName.trim().replace(/\s+/g, " ");
    if (!cleanedName) {
      setProfileMessage("Display name cannot be empty.");
      return;
    }
    setProfilePending(true);
    setProfileMessage("");
    try {
      const accessToken = await getAccessToken();
      if (!accessToken) throw new Error("Your session has expired. Please sign in again.");
      let avatarPath = account?.profile.avatar_path ?? null;
      if (avatarFile) {
        avatarPath = `${user.id}/avatar`;
        const { error } = await supabase.storage
          .from("avatars")
          .upload(avatarPath, avatarFile, {
            upsert: true,
            contentType: avatarFile.type,
            cacheControl: "3600",
          });
        if (error) throw error;
      }
      const response = await updateMyAccountProfile(accessToken, {
        display_name: cleanedName,
        avatar_path: avatarPath,
      });
      const { error: metadataError } = await supabase.auth.updateUser({
        data: { display_name: cleanedName },
      });
      if (metadataError) throw metadataError;
      setAccount(response);
      setDisplayName(response.profile.display_name || cleanedName);
      setAvatarFile(null);
      setAvatarPreview("");
      setProfileMessage("Profile updated.");
      router.refresh();
    } catch (error) {
      setProfileMessage(readableError(error, "Could not update your profile."));
    } finally {
      setProfilePending(false);
    }
  }

  async function removeAvatar() {
    if (!account?.profile.avatar_path) return;
    setProfilePending(true);
    setProfileMessage("");
    try {
      const accessToken = await getAccessToken();
      if (!accessToken) throw new Error("Your session has expired. Please sign in again.");
      const response = await updateMyAccountProfile(accessToken, { avatar_path: null });
      setAccount(response);
      setAvatarFile(null);
      setAvatarPreview("");
      setProfileMessage("Avatar removed.");
    } catch (error) {
      setProfileMessage(readableError(error, "Could not remove your avatar."));
    } finally {
      setProfilePending(false);
    }
  }

  async function updatePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordMessage("");
    if (newPassword.length < 8) {
      setPasswordMessage("Use at least eight characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordMessage("The passwords do not match.");
      return;
    }
    setPasswordPending(true);
    const { error } = await supabase.auth.updateUser({ password: newPassword });
    setPasswordPending(false);
    if (error) {
      setPasswordMessage(error.message);
      return;
    }
    setNewPassword("");
    setConfirmPassword("");
    setPasswordMessage("Password updated.");
  }

  async function logout() {
    setLogoutPending(true);
    setProfileMessage("");
    try {
      await signOut();
      router.replace("/");
      router.refresh();
    } catch (error) {
      setProfileMessage(readableError(error, "Could not sign out."));
      setLogoutPending(false);
    }
  }

  async function deleteAccount() {
    if (deleteConfirmation !== "DELETE") {
      setDeleteMessage('Type "DELETE" to confirm.');
      return;
    }
    setDeletePending(true);
    setDeleteMessage("");
    try {
      const accessToken = await getAccessToken();
      if (!accessToken) throw new Error("Your session has expired. Please sign in again.");
      await deleteMyAccount(accessToken);
      await supabase.auth.signOut({ scope: "local" });
      localStorage.removeItem("seoulmate:watchlist");
      router.replace("/");
      router.refresh();
    } catch (error) {
      setDeleteMessage(readableError(error, "Could not delete your account."));
      setDeletePending(false);
    }
  }

  const profile = account?.profile;
  const statistics = account?.statistics;
  const avatarSrc = avatarPreview || (
    profile?.avatar_url ? `${profile.avatar_url}?v=${encodeURIComponent(profile.updated_at)}` : ""
  );

  return (
    <div className="account-layout">
      <section className="account-card account-summary">
        <div className="account-avatar" aria-hidden={!avatarSrc}>
          {avatarSrc ? (
            <Image src={avatarSrc} alt={`${displayName} avatar`} width={96} height={96} unoptimized />
          ) : (
            <span aria-hidden="true">{displayName.charAt(0).toUpperCase()}</span>
          )}
        </div>
        <div>
          <span className="eyebrow">Signed in</span>
          <h2>{profile?.display_name || displayName}</h2>
          <p>{email}</p>
        </div>
        <button className="secondary-button account-logout" type="button" onClick={logout} disabled={logoutPending}>
          <LogOut size={17} /> {logoutPending ? "Signing out…" : "Sign out"}
        </button>
      </section>

      <section className="account-section">
        <div className="account-section-heading"><UserRound size={20} /><div><h2>Profile</h2><p>Update how your account appears in SeoulMate.</p></div></div>
        <form className="account-form" onSubmit={saveProfile}>
          <label><span>Display name</span><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} maxLength={100} required /></label>
          <label className="avatar-upload"><span>Avatar</span><input type="file" accept="image/jpeg,image/png,image/webp" onChange={selectAvatar} /><small>JPEG, PNG, or WebP. Maximum 2 MB.</small></label>
          <div className="account-form-actions">
            <button className="primary-button" type="submit" disabled={profilePending || loading}>{profilePending ? "Saving…" : "Save profile"}</button>
            {profile?.avatar_path && <button className="secondary-button" type="button" onClick={removeAvatar} disabled={profilePending}>Remove avatar</button>}
          </div>
          {profileMessage && <p className="auth-message" role="status">{profileMessage}</p>}
        </form>
      </section>

      <section className="account-section">
        <div className="account-section-heading"><KeyRound size={20} /><div><h2>Password</h2><p>Choose a new password for future sign-ins.</p></div></div>
        <form className="account-form" onSubmit={updatePassword}>
          <label><span>New password</span><input type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} minLength={8} required /></label>
          <label><span>Confirm password</span><input type="password" autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} minLength={8} required /></label>
          <button className="primary-button" type="submit" disabled={passwordPending}>{passwordPending ? "Updating…" : "Change password"}</button>
          {passwordMessage && <p className="auth-message" role="status">{passwordMessage}</p>}
        </form>
      </section>

      <section className="account-section account-statistics">
        <div className="account-section-heading"><Activity size={20} /><div><h2>Profile statistics</h2><p>Your current saved and completed activity.</p></div></div>
        {loading ? <div className="profile-loading"><span /><span /></div> : statistics && (
          <div className="account-stat-grid">
            <div className="stat-box"><strong>{statistics.saved_total}</strong><span>saved dramas</span></div>
            <div className="stat-box"><strong>{statistics.active_total}</strong><span>active titles</span></div>
            <div className="stat-box"><strong>{statistics.watching}</strong><span>watching</span></div>
            <div className="stat-box"><strong>{statistics.completed}</strong><span>completed</span></div>
            <div className="stat-box"><strong>{statistics.ratings_total}</strong><span>ratings</span></div>
            <div className="stat-box"><strong>{statistics.average_rating ?? "—"}</strong><span>average rating</span></div>
          </div>
        )}
      </section>

      <section className="account-section account-danger">
        <div className="account-section-heading"><Trash2 size={20} /><div><h2>Delete account</h2><p>Permanently remove your account, profile, watchlist, ratings, preferences, activity associations, and avatar.</p></div></div>
        <label><span>Type DELETE to confirm</span><input value={deleteConfirmation} onChange={(event) => setDeleteConfirmation(event.target.value)} autoComplete="off" /></label>
        <button className="danger-button" type="button" onClick={deleteAccount} disabled={deletePending}>{deletePending ? "Deleting account…" : "Delete my account"}</button>
        {deleteMessage && <p className="auth-message" role="alert">{deleteMessage}</p>}
      </section>
    </div>
  );
}
