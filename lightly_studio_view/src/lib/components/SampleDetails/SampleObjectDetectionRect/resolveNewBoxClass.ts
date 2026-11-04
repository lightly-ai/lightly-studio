import type { BoundingBox } from '$lib/types';

/** The class for a new box: the sticky class, else the class picked at the box (null: drop it). */
export const resolveNewBoxClass = async ({
    stickyClass,
    bbox,
    requestClass
}: {
    stickyClass: string | undefined;
    bbox: BoundingBox;
    requestClass: (bbox: BoundingBox) => Promise<string | null>;
}): Promise<string | null> => (stickyClass ? stickyClass : requestClass(bbox));
