import { UploadForm } from "@/components/upload/upload-form";

export default function UploadPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Add Track</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Drop an MP3, WAV, or FLAC. The original is archived to B2, then
          Demucs splits it into vocals, drums, bass, and other stems.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <UploadForm />
      </div>
    </div>
  );
}
