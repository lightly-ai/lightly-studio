interface SupportsTaskParams {
    capabilities: string[] | undefined;
    task: 'object_detection' | 'segmentation';
}

/**
 * Tell whether a model can serve a task.
 *
 * A model that only serves segmentation can still produce object detections, because the
 * backend converts each mask to its bounding box.
 */
export function supportsTask({ capabilities, task }: SupportsTaskParams): boolean {
    const served = capabilities ?? [];
    if (served.includes(`${task}_image_bytes`)) return true;
    return task === 'object_detection' && served.includes('segmentation_image_bytes');
}
