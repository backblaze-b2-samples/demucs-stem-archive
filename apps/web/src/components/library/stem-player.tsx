"use client";

import { Download, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ApiError, getDownloadUrl } from "@/lib/api-client";
import { usePreviewUrl } from "@/lib/queries";
import type { Stem } from "@demucs-stem-archive/shared";

const ROLE_LABEL: Record<string, string> = {
  vocals: "Vocals",
  drums: "Drums",
  bass: "Bass",
  other: "Other",
};

interface StemPlayerProps {
  stem: Stem;
}

/**
 * Inline stem row: a streaming <audio> element fed by a presigned preview URL
 * (which does NOT bump the download counter) plus a download button that uses
 * the attachment-disposition download URL. The preview URL is fetched lazily
 * through the shared TanStack Query hook.
 */
export function StemPlayer({ stem }: StemPlayerProps) {
  const { data, isLoading } = usePreviewUrl(stem.key, true);
  const streamUrl = data?.url ?? null;

  const handleDownload = async () => {
    try {
      const { url } = await getDownloadUrl(stem.key);
      window.open(url, "_blank");
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : "Download failed";
      toast.error(detail);
    }
  };

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border bg-muted/30 p-3 sm:flex-row sm:items-center">
      <div className="flex items-center gap-2 sm:w-28 shrink-0">
        <span className="h-1.5 w-1.5 rounded-full bg-primary" />
        <span className="text-sm font-medium">
          {ROLE_LABEL[stem.role] ?? stem.role}
        </span>
        <span className="ml-auto sm:ml-0 font-mono text-xs text-muted-foreground tabular-nums">
          {stem.size_human}
        </span>
      </div>
      <div className="flex-1 min-w-0">
        {isLoading ? (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Loading stream…
          </div>
        ) : streamUrl ? (
          <audio controls preload="none" src={streamUrl} className="h-9 w-full" />
        ) : (
          <span className="text-xs text-muted-foreground">Stream unavailable</span>
        )}
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={handleDownload}
        className="h-8 shrink-0"
      >
        <Download className="h-3.5 w-3.5" />
        Download
      </Button>
    </div>
  );
}
