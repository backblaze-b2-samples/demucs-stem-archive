// ---- Full-bucket explorer (kept from the starter) ----

export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// ---- Stem archive (demucs-stem-archive) ----

export type StemRole = "vocals" | "drums" | "bass" | "other";
export const STEM_ROLES: StemRole[] = ["vocals", "drums", "bass", "other"];

export type SeparationStatus = "pending" | "processing" | "done" | "failed";

export interface Stem {
  role: StemRole;
  key: string;
  size_bytes: number;
  size_human: string;
  uploaded_at: string | null;
}

export interface TrackSummary {
  track_id: string;
  title: string;
  original_key: string;
  original_size_bytes: number;
  original_size_human: string;
  uploaded_at: string;
  status: SeparationStatus;
  stems_present: StemRole[];
  stem_count: number;
  error: string | null;
}

export interface TrackDetail extends TrackSummary {
  stems: Stem[];
}

export interface ArchiveStats {
  track_count: number;
  stem_count: number;
  object_count: number;
  total_size_bytes: number;
  total_size_human: string;
  amplification_ratio: number;
  separations_today: number;
  processing_count: number;
  failed_count: number;
}

export interface DailyActivity {
  date: string;
  tracks: number;
  stems: number;
}

export interface IngestResponse {
  track_id: string;
  title: string;
  original_key: string;
  status: SeparationStatus;
}
