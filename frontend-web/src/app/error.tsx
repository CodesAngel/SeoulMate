"use client";

import { useEffect } from "react";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="shell section">
      <div className="empty-state" role="alert">
        <h2>Something interrupted this story</h2>
        <p>Please try loading this page again.</p>
        <button className="primary-button" type="button" onClick={reset}>
          Try again
        </button>
      </div>
    </div>
  );
}
