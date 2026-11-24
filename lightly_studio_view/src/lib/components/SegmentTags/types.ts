import type { AnnotationViewTag } from '$lib/api/lightly_studio_local';

/** A tag on a sample. Without a tag id it is shown but cannot be removed. */
export type TagItem = Pick<AnnotationViewTag, 'name'> & Partial<Pick<AnnotationViewTag, 'tag_id'>>;
