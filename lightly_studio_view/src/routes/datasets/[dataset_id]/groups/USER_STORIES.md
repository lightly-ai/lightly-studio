# User Stories for Working with Groups

Below are typical tasks or user stories for someone working with groups in Lightly Studio:

## 🧱 1. Create a Grouped Dataset

**As a dataset engineer**, I want to create a dataset where related components belong to logical groups, so I can organize multi-page documents, multi-view images, or structured data together.

**Actions:**
- Create a new dataset in Lightly Studio
- Upload components that belong to the same logical group (e.g., front page, back page, signature page of a document)
- Lightly Studio automatically organizes them into groups

**Example Use Case:**
- Uploading passport scans with front page, back page, and signature page
- Each group represents a complete document set

✔ This lets you work with complete document sets rather than isolated images.

## 🧩 2. Browse and Filter Component Groups

**As someone curating data**, I want to browse groups and filter by component type so I can quickly find specific document types or components.

**Scenario:**
- You have uploaded hundreds of document groups
- You need to review only "signature pages" across all documents

**Actions:**
- Use the component groups menu in the left sidebar
- Click on a component type (e.g., "Signature Page", "Front Page")
- View all components of that type across all groups
- Apply additional filters as needed

This ensures you can efficiently navigate large grouped datasets by focusing on specific component types.

## 🔍 3. View and Annotate Complete Groups

**As an annotator**, I want to view all components of a group together when inspecting or labeling data, so I don't lose the context between related pages or views.

**Actions:**
- Click on a group in the grid view
- See all components (front page, back page, signature, attachments) displayed together
- Navigate between components within the same group
- Apply labels or annotations while maintaining group context

This is critical for workflows where understanding the complete document or multi-view scene matters for accurate annotation.

## 🕹 4. Configure Default Component Display

**As a data explorer**, I want to specify which component of a group appears by default in the grid view (e.g., show "front page" as the thumbnail).

**Actions:**
- Configure dataset settings to set the default component type
- Grid view displays the specified component as the group thumbnail
- Other components are accessible by clicking into the group

**Example:**
- Set "front page" as default for passport documents
- Grid shows front page thumbnails for quick scanning
- Click any group to see all components

✔ Helps streamline visual review of large grouped datasets.

## ⚙️ 5. Work With Mixed Media Types in Groups

**As a model trainer**, I want to work with different media types within a single group (images, PDFs, scans) as part of one unified dataset, so I can run joint workflows and training pipelines.

**Actions:**
- Upload groups containing mixed media (e.g., photo ID + PDF document + signature image)
- Lightly Studio handles different media types within the same group
- Standard operations (search, filter, export) work across all component types
- Export maintains group structure for downstream ML pipelines

## 📊 6. Analyze and Filter Groups by Metadata

**As an analyst**, I want to filter and analyze groups based on metadata, quality scores, or other attributes, so I can identify problematic groups or high-quality subsets.

**Actions:**
- Filter groups by metadata fields (upload date, quality score, document type)
- View statistics across component types (e.g., "245 front pages, 189 back pages")
- Create saved views of filtered groups for later review
- Export filtered subsets while maintaining group structure

## 🗺️ Practical Examples of Where Groups Help

Here are concrete scenarios where grouping improves your workflow in Lightly Studio:

| Use Case | Why Grouping Helps |
|----------|-------------------|
| Identity document verification | Keep front page, back page, and signature together for complete document review |
| Multi-page forms processing | Organize all pages of a form as one logical unit for data extraction |
| Multi-camera capture | Link images from different camera angles of the same scene |
| Medical imaging | Group related scans (X-ray, MRI, CT) of the same patient/session |
| Product photography | Keep multiple product shots (front, side, detail) together for e-commerce |
