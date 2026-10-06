"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Edit3, MessageSquare, Send, ShieldAlert, Trash2 } from "lucide-react";
import type { CommunityComment } from "@/lib/types";
import { useAuth } from "@/components/auth-provider";
import {
  createCommunityComment,
  deleteCommunityComment,
  updateCommunityComment,
} from "@/lib/api";
import { SpoilerContent } from "@/components/spoiler-content";

interface CommunityCommentsProps {
  postId: string;
  comments: CommunityComment[];
  onRefresh: () => void;
  isLoading?: boolean;
}

function formatRelativeTime(dateStr: string): string {
  try {
    const diffMs = Date.now() - new Date(dateStr).getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffDay > 0) return `${diffDay}d ago`;
    if (diffHour > 0) return `${diffHour}h ago`;
    if (diffMin > 0) return `${diffMin}m ago`;
    return "just now";
  } catch {
    return "recently";
  }
}

export function CommunityComments({
  postId,
  comments,
  onRefresh,
  isLoading = false,
}: CommunityCommentsProps) {
  const { user, getAccessToken } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  // Create state
  const [newBody, setNewBody] = useState("");
  const [newSpoiler, setNewSpoiler] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  // Edit state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editBody, setEditBody] = useState("");
  const [editSpoiler, setEditSpoiler] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  // Delete state
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!user) {
      router.push(`/auth/login?returnUrl=${encodeURIComponent(pathname)}`);
      return;
    }

    const trimmed = newBody.trim();
    if (!trimmed) return;

    setIsSubmitting(true);
    setSubmitError("");

    try {
      const token = await getAccessToken();
      if (!token) throw new Error("Authentication required");

      await createCommunityComment(
        postId,
        { body: trimmed, contains_spoilers: newSpoiler },
        token,
      );
      setNewBody("");
      setNewSpoiler(false);
      onRefresh();
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : "Failed to post comment");
    } finally {
      setIsSubmitting(false);
    }
  }

  function startEdit(comment: CommunityComment) {
    setEditingId(comment.id);
    setEditBody(comment.body);
    setEditSpoiler(comment.contains_spoilers);
  }

  async function handleSaveEdit(commentId: string) {
    const trimmed = editBody.trim();
    if (!trimmed) return;

    setIsEditing(true);
    try {
      const token = await getAccessToken();
      if (!token) throw new Error("Authentication required");

      await updateCommunityComment(
        commentId,
        { body: trimmed, contains_spoilers: editSpoiler },
        token,
      );
      setEditingId(null);
      onRefresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update comment");
    } finally {
      setIsEditing(false);
    }
  }

  async function handleDelete(commentId: string) {
    setIsDeleting(true);
    try {
      const token = await getAccessToken();
      if (!token) throw new Error("Authentication required");

      await deleteCommunityComment(commentId, token);
      setDeletingId(null);
      onRefresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete comment");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <section className="community-comments-section" id="comments">
      <div className="comments-section-header">
        <MessageSquare size={20} className="comments-header-icon" />
        <h2>Comments ({comments.length})</h2>
      </div>

      {/* Comment Composer */}
      {user ? (
        <form className="comment-composer-form" onSubmit={handleCreate}>
          <label htmlFor="new-comment-textarea" className="composer-label">
            Share your thoughts (spoiler-safe)
          </label>
          <textarea
            id="new-comment-textarea"
            className="comment-textarea"
            placeholder="Write a comment… Be kind and tag spoilers if discussing plot secrets!"
            value={newBody}
            onChange={(e) => setNewBody(e.target.value)}
            maxLength={1000}
            rows={3}
            required
          />

          <div className="composer-toolbar-row">
            <div className="composer-options-left">
              <label className="spoiler-toggle-checkbox">
                <input
                  type="checkbox"
                  checked={newSpoiler}
                  onChange={(e) => setNewSpoiler(e.target.checked)}
                />
                <ShieldAlert size={14} className="spoiler-checkbox-icon" />
                <span>Mark as spoiler</span>
              </label>
              <span className="char-counter">
                {newBody.length}/1000
              </span>
            </div>

            <button
              type="submit"
              className="primary-button comment-submit-btn"
              disabled={isSubmitting || !newBody.trim()}
            >
              <Send size={15} />
              <span>{isSubmitting ? "Posting…" : "Post Comment"}</span>
            </button>
          </div>

          {submitError && (
            <div className="error-banner" role="alert">
              {submitError}
            </div>
          )}
        </form>
      ) : (
        <div className="comment-signin-prompt">
          <p>Want to join this discussion?</p>
          <Link
            href={`/auth/login?returnUrl=${encodeURIComponent(pathname)}`}
            className="primary-button prompt-signin-btn"
          >
            Sign in to comment
          </Link>
        </div>
      )}

      {/* Comments List */}
      {isLoading ? (
        <div className="comments-loading-state">
          <p className="muted">Loading comments…</p>
        </div>
      ) : comments.length === 0 ? (
        <div className="empty-state comments-empty">
          <MessageSquare size={32} style={{ margin: "0 auto 8px", opacity: 0.6 }} />
          <h3>No comments yet</h3>
          <p>Be the first to share your thoughts on this discussion.</p>
        </div>
      ) : (
        <div className="comments-stream-list">
          {comments.map((comment) => {
            const isSelf = comment.is_author;
            const isBeingEdited = editingId === comment.id;
            const isConfirmingDelete = deletingId === comment.id;

            const exactDate = new Date(comment.created_at).toLocaleString(undefined, {
              dateStyle: "medium",
              timeStyle: "short",
            });

            return (
              <div key={comment.id} className="comment-item-card">
                <div className="comment-item-header">
                  <div className="comment-author-pill">
                    <div className="comment-avatar-bubble">
                      {comment.author.avatar_url ? (
                        /* eslint-disable-next-line @next/next/no-img-element */
                        <img src={comment.author.avatar_url} alt={comment.author.display_name} />
                      ) : (
                        comment.author.display_name.slice(0, 1).toUpperCase()
                      )}
                    </div>
                    <div>
                      <strong className="comment-author-name">
                        {comment.author.display_name}
                      </strong>
                      <time
                        className="comment-timestamp"
                        dateTime={comment.created_at}
                        title={exactDate}
                      >
                        {formatRelativeTime(comment.created_at)}
                      </time>
                    </div>
                  </div>

                  {isSelf && !isBeingEdited && (
                    <div className="comment-author-actions">
                      <button
                        type="button"
                        className="comment-action-btn"
                        onClick={() => startEdit(comment)}
                        aria-label="Edit comment"
                      >
                        <Edit3 size={13} />
                        <span>Edit</span>
                      </button>
                      <button
                        type="button"
                        className="comment-action-btn delete"
                        onClick={() => setDeletingId(comment.id)}
                        aria-label="Delete comment"
                      >
                        <Trash2 size={13} />
                        <span>Delete</span>
                      </button>
                    </div>
                  )}
                </div>

                {/* Inline Delete Confirmation */}
                {isConfirmingDelete && (
                  <div className="inline-confirm-box" role="alert">
                    <p>Delete this comment?</p>
                    <div className="inline-confirm-actions">
                      <button
                        type="button"
                        className="danger-button confirm-delete-btn"
                        onClick={() => handleDelete(comment.id)}
                        disabled={isDeleting}
                      >
                        {isDeleting ? "Deleting…" : "Delete"}
                      </button>
                      <button
                        type="button"
                        className="ghost-button"
                        onClick={() => setDeletingId(null)}
                        disabled={isDeleting}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {/* Body or Edit Form */}
                {isBeingEdited ? (
                  <div className="comment-edit-box">
                    <textarea
                      className="comment-textarea"
                      value={editBody}
                      onChange={(e) => setEditBody(e.target.value)}
                      maxLength={1000}
                      rows={3}
                    />
                    <div className="comment-edit-actions">
                      <label className="spoiler-toggle-checkbox">
                        <input
                          type="checkbox"
                          checked={editSpoiler}
                          onChange={(e) => setEditSpoiler(e.target.checked)}
                        />
                        <span>Contains spoilers</span>
                      </label>
                      <div className="edit-btn-group">
                        <button
                          type="button"
                          className="ghost-button"
                          onClick={() => setEditingId(null)}
                          disabled={isEditing}
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          className="primary-button"
                          onClick={() => handleSaveEdit(comment.id)}
                          disabled={isEditing || !editBody.trim()}
                        >
                          {isEditing ? "Saving…" : "Save"}
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="comment-item-body">
                    <SpoilerContent isSpoiler={comment.contains_spoilers}>
                      <p className="comment-body-text">{comment.body}</p>
                    </SpoilerContent>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
