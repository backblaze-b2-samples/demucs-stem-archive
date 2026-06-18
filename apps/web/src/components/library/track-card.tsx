"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Loader2,
  Music,
  Trash2,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StemPlayer } from "./stem-player";
import { useTrack } from "@/lib/queries";
import { formatDate } from "@/lib/utils";
import type {
  SeparationStatus,
  StemRole,
  TrackSummary,
} from "@demucs-stem-archive/shared";

const STATUS_BADGE: Record<
  SeparationStatus,
  { label: string; className: string }
> = {
  pending: { label: "Queued", className: "bg-muted text-muted-foreground" },
  processing: {
    label: "Separating…",
    className: "bg-[var(--attention-subtle)] text-[var(--attention)]",
  },
  done: {
    label: "4 stems",
    className: "bg-[color-mix(in_oklab,var(--success)_15%,transparent)] text-[var(--success)]",
  },
  failed: { label: "Failed", className: "bg-destructive/10 text-destructive" },
};

const ALL_ROLES: StemRole[] = ["vocals", "drums", "bass", "other"];

interface TrackCardProps {
  track: TrackSummary;
  onDelete: (track: TrackSummary) => void;
}

export function TrackCard({ track, onDelete }: TrackCardProps) {
  const [open, setOpen] = useState(false);
  const detail = useTrack(track.track_id, open);
  const badge = STATUS_BADGE[track.status];
  const isProcessing = track.status === "pending" || track.status === "processing";

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-3">
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex flex-1 items-center gap-3 text-left min-w-0"
        >
          {open ? (
            <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
          )}
          <Music className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="font-medium truncate">{track.title}</span>
          <span className="hidden sm:inline font-mono text-xs text-muted-foreground tabular-nums">
            {track.original_size_human}
          </span>
          <span className="hidden md:inline text-xs text-muted-foreground">
            {formatDate(track.uploaded_at)}
          </span>
        </button>
        <Badge className={`shrink-0 gap-1 ${badge.className}`}>
          {isProcessing && <Loader2 className="h-3 w-3 animate-spin" />}
          {badge.label}
        </Badge>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive"
          onClick={() => onDelete(track)}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Stem chips — which of the 4 roles already exist in B2. */}
      <div className="flex flex-wrap gap-1.5 px-4 pb-3 pl-11">
        {ALL_ROLES.map((role) => {
          const present = track.stems_present.includes(role);
          return (
            <span
              key={role}
              className={`rounded px-2 py-0.5 text-[11px] font-medium ${
                present
                  ? "bg-primary/10 text-primary"
                  : "bg-muted text-muted-foreground/60"
              }`}
            >
              {role}
            </span>
          );
        })}
      </div>

      {open && (
        <div className="border-t border-border px-4 py-3 space-y-2 bg-muted/20">
          {track.status === "failed" ? (
            <p className="text-sm text-destructive">
              Separation failed: {track.error ?? "unknown error"}
            </p>
          ) : detail.isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : detail.data && detail.data.stems.length > 0 ? (
            detail.data.stems.map((stem) => (
              <StemPlayer key={stem.key} stem={stem} />
            ))
          ) : (
            <p className="text-sm text-muted-foreground">
              Stems not ready yet — separation is still running.
            </p>
          )}
        </div>
      )}
    </Card>
  );
}
