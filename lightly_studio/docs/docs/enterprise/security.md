# Security Considerations

Lightly is designed for secure enterprise-grade machine learning workflows. Across all deployment
models, raw images and videos are never stored on Lightly servers.

## Certifications

- ISO 27001: Lightly is ISO 27001 certified, ensuring the confidentiality, integrity, and
  availability of your data through robust information security management.
- GDPR: Lightly is fully compliant with the General Data Protection Regulation (GDPR), protecting
  user privacy and upholding strict data handling standards.

## Data Sent to or Stored by Lightly

What Lightly stores depends on the deployment model:

- OSS: Only analytics data is sent to Lightly. The OSS version can also be run fully offline.

- Lightly-Hosted: To operate the service, Lightly stores analytics, user account information, and dataset metadata,
including annotations. Raw images and videos are streamed from your storage to the browser when
needed, but are never stored on Lightly servers.

- On-Premise: Nothing is sent to Lightly. The deployment can be fully offline and air-gapped.