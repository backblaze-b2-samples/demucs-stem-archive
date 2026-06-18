"use client";

import { useState } from "react";
import { Music, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { TrackCard } from "./track-card";
import { ApiError } from "@/lib/api-client";
import { useDeleteTrack, useTracks } from "@/lib/queries";
import type { TrackSummary } from "@demucs-stem-archive/shared";

export function TrackLibrary() {
  const { data: tracks = [], isLoading, isFetching, error, refetch } = useTracks();
  const deleteMutation = useDeleteTrack();
  const [deleteTarget, setDeleteTarget] = useState<TrackSummary | null>(null);

  const confirmDelete = () => {
    if (!deleteTarget) return;
    const target = deleteTarget;
    deleteMutation.mutate(target.track_id, {
      onSuccess: () => toast.success(`${target.title} and its stems deleted`),
      onError: (err) => {
        const detail = err instanceof ApiError ? err.message : "Failed to delete track";
        toast.error(detail);
      },
      onSettled: () => setDeleteTarget(null),
    });
  };

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between border-b border-border py-4 px-5 space-y-0">
          <CardTitle className="card-title">Tracks</CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            className="h-7 text-xs"
            disabled={isFetching}
          >
            <RefreshCw className={`h-3.5 w-3.5 mr-1 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </CardHeader>
        <CardContent className="p-3">
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : error ? (
            <ErrorState error={error} onRetry={() => refetch()} />
          ) : tracks.length === 0 ? (
            <EmptyState
              icon={Music}
              title="No tracks yet"
              description="Add an MP3, WAV, or FLAC to archive it and split it into stems."
            />
          ) : (
            <div className="space-y-2">
              {tracks.map((track) => (
                <TrackCard
                  key={track.track_id}
                  track={track}
                  onDelete={setDeleteTarget}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <AlertDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete track?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently deletes <strong>{deleteTarget?.title}</strong> and
              every stem under its prefix in B2. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
