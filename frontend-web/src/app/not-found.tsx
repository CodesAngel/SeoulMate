import Link from "next/link";

export default function NotFound() {
  return <div className="shell section"><div className="empty-state"><span className="eyebrow">404</span><h2>This episode does not exist</h2><p>Return to discovery and find a better story.</p><Link href="/" className="primary-button" style={{ display: "inline-block", marginTop: 18 }}>Back home</Link></div></div>;
}
