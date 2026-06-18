"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  deleteFile,
  deleteTrack,
  getArchiveActivity,
  getArchiveStats,
  getFiles,
  getFileStats,
  getPreviewUrl,
  getTrack,
  getTracks,
  getUploadActivity,
} from "@/lib/api-client";
import type {
  FileMetadata,
  TrackDetail,
  TrackSummary,
} from "@demucs-stem-archive/shared";

// Single source of truth for query keys. Keep these tightly scoped so that
// invalidating one branch doesn't blow away unrelated caches, and so an IDE
// "find usages" of `qk.*` reveals every consumer.
export const qk = {
  all: ["b2"] as const,
  // Stem archive (tracks)
  tracks: () => [...qk.all, "tracks"] as const,
  track: (id: string) => [...qk.all, "tracks", "detail", id] as const,
  archiveStats: () => [...qk.all, "tracks", "stats"] as const,
  archiveActivity: (days: number) =>
    [...qk.all, "tracks", "activity", days] as const,
  // Full-bucket explorer (files)
  files: (prefix?: string, limit?: number) =>
    [...qk.all, "files", prefix ?? "", limit ?? 100] as const,
  stats: () => [...qk.all, "stats"] as const,
  uploadActivity: (days: number) =>
    [...qk.all, "stats", "activity", days] as const,
  preview: (key: string) => [...qk.all, "preview", key] as const,
};

// Poll every 4s while any track is still pending/processing so the Library
// reflects separation progress without a manual refresh.
const PROCESSING = new Set(["pending", "processing"]);

function refetchWhileProcessing(tracks: TrackSummary[] | undefined): number | false {
  if (tracks && tracks.some((t) => PROCESSING.has(t.status))) return 4_000;
  return false;
}

// ---- Stem archive (tracks) ----

export function useTracks() {
  return useQuery<TrackSummary[], ApiError>({
    queryKey: qk.tracks(),
    queryFn: getTracks,
    // refetchInterval receives the query so we can stop polling once every
    // job is done/failed.
    refetchInterval: (query) => refetchWhileProcessing(query.state.data),
  });
}

// Lazily fetched per-track detail (includes stem keys + sizes). Enabled only
// when a card is expanded. While the track is still processing it re-polls so
// stem rows appear as separation finishes.
export function useTrack(trackId: string, enabled: boolean) {
  return useQuery<TrackDetail, ApiError>({
    queryKey: qk.track(trackId),
    queryFn: () => getTrack(trackId),
    enabled,
    refetchInterval: (query) =>
      query.state.data && PROCESSING.has(query.state.data.status) ? 4_000 : false,
  });
}

export function useArchiveStats() {
  return useQuery({
    queryKey: qk.archiveStats(),
    queryFn: getArchiveStats,
    refetchInterval: (query) =>
      query.state.data && query.state.data.processing_count > 0 ? 4_000 : false,
  });
}

export function useArchiveActivity(days = 7) {
  return useQuery({
    queryKey: qk.archiveActivity(days),
    queryFn: () => getArchiveActivity(days),
  });
}

export function useDeleteTrack() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (trackId: string) => deleteTrack(trackId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// ---- Full-bucket explorer (files) ----

export function useFiles(prefix = "", limit = 100) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.files(prefix, limit),
    queryFn: () => getFiles(prefix, limit),
  });
}

export function useFileStats() {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: getFileStats,
  });
}

export function useUploadActivity(days = 7) {
  return useQuery({
    queryKey: qk.uploadActivity(days),
    queryFn: () => getUploadActivity(days),
  });
}

// Presigned preview URL — only fetched when `enabled` is true (e.g., when
// the dialog opens for a specific file, or an audio player mounts). Kept
// short-lived (60s) because the URL itself has a presigned expiry and is
// cheap to regenerate.
export function usePreviewUrl(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.preview(key ?? ""),
    queryFn: () => getPreviewUrl(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileKey: string) => deleteFile(fileKey),
    // After delete, blow away every cached file list + stats. Cheap and
    // correct — consumers re-fetch lazily as components remount.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}
