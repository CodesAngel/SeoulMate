import { Clapperboard } from "lucide-react";

export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <span className="brand-lockup" aria-label="SeoulMate">
      <span className="brand-icon" aria-hidden="true">
        <Clapperboard size={18} strokeWidth={2.2} />
      </span>
      {!compact && (
        <span className="brand-name">
          Seoul<span>Mate</span>
        </span>
      )}
    </span>
  );
}
