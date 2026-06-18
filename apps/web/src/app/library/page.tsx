import Link from "next/link";
import { Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { TrackLibrary } from "@/components/library/track-library";

export default function LibraryPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Stem Library</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Every track and its four stems, archived in Backblaze B2. Stream or
            download any stem straight from the bucket.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/upload">
            <Upload className="h-3.5 w-3.5" />
            Add track
          </Link>
        </Button>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <TrackLibrary />
      </div>
    </div>
  );
}
