import type { ImageView } from '$lib/api/lightly_studio_local';
import type { SortExpr } from '$lib/hooks/useImagesInfinite/types';

type UseSampleOrderValueParams = {
    sample: ImageView;
    sortExpr?: SortExpr | null;
};

const NUMERIC_IMAGE_FIELDS = new Set(['width', 'height']);

function asNumber(value: unknown): number | undefined {
    if (typeof value === 'number' && Number.isFinite(value)) {
        return value;
    }
    if (typeof value === 'string' && value.trim().length > 0) {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : undefined;
    }
    return undefined;
}

function resolveImageFieldValue(sample: ImageView, fieldName: string): number | undefined {
    if (!NUMERIC_IMAGE_FIELDS.has(fieldName)) {
        return undefined;
    }

    const value = sample[fieldName as keyof Pick<ImageView, 'width' | 'height'>];
    return asNumber(value);
}

function resolveMetadataFieldValue(sample: ImageView, fieldName: string): number | undefined {
    const metadataValue = sample.metadata_dict?.data?.[fieldName];
    return asNumber(metadataValue);
}

export function useSampleOrderValue({
    sample,
    sortExpr
}: UseSampleOrderValueParams): number | undefined {
    if (!sortExpr) return undefined;

    if (sortExpr.source === 'evaluation_metric') {
        // Evaluation metric values are currently not part of ImageView payload.
        return undefined;
    }

    if (sortExpr.source === 'image') {
        return resolveImageFieldValue(sample, sortExpr.field_name);
    }

    if (sortExpr.source === 'metadata') {
        if (!sortExpr.is_numeric) return undefined;
        return resolveMetadataFieldValue(sample, sortExpr.field_name);
    }

    return undefined;
}
