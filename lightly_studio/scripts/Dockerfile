# Container for the QA sampler Cloud Run Job.
# The sampler is standalone (stdlib + google-cloud-storage only), so the image
# stays tiny and does not pull in the lightly_studio package or its heavy deps.
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir "google-cloud-storage>=2.18.0"

COPY sample_gcs_review.py /app/sample_gcs_review.py

ENTRYPOINT ["python", "/app/sample_gcs_review.py"]
# Default to applying moves; a run can override args to dry-run.
CMD ["--apply"]
