# Issue 2: B2 Standards

## Goal

Make the sample pass the mandatory B2 quality-keeper standards:

- B2 access stays on the S3-compatible API.
- Every S3 client sends a custom sample user agent with the
  `backblaze-b2-samples` marker.
- Configuration uses the standard B2 env vars:
  `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`,
  `B2_REGION`, and `B2_PUBLIC_URL_BASE`.

## Plan

1. Remove the non-standard endpoint env override and derive the S3 endpoint
   strictly from `B2_REGION`.
2. Validate the region during API startup and before creating a boto3 client so
   malformed env values cannot become outbound endpoint URLs.
3. Update the boto3 user agent to include the Backblaze sample-suite marker.
4. Add focused backend tests for env parsing, endpoint derivation, region
   validation, public URL normalization, and S3 client construction.
5. Update architecture/security/setup docs with the standardized B2 behavior
   and the `B2_ENDPOINT` removal migration note.
6. Run backend lint/tests, structure checks, and frontend lint.
