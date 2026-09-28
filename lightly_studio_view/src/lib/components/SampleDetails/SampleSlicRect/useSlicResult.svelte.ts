import { loadSuperpixelsForImage } from '$lib/utils/slic';
import { maskToDataUrl } from '$lib/components/SampleAnnotation/utils';
import parseColor from '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/parseColor';

interface SlicResultProps {
    imageUrl: string;
    level: Parameters<typeof loadSuperpixelsForImage>[0]['level'];
    color: string;
}

export function useSlicResult(getProps: () => SlicResultProps) {
    const { imageUrl, level, color } = $derived(getProps());
    let result = $state<Awaited<ReturnType<typeof loadSuperpixelsForImage>> | null>(null);
    let status = $state<'computing' | 'ready' | 'error'>('computing');
    const boundaryDataUrl = $derived.by(() => {
        if (!result) return '';
        const { boundaries, width, height } = result.segmentation;
        // Translucent boundaries keep the underlying image visible.
        return maskToDataUrl(boundaries, width, height, { ...parseColor(color), a: 170 });
    });

    $effect(() => {
        let active = true;
        result = null;
        status = 'computing';
        void loadSuperpixelsForImage({ imageUrl, level }).then(
            (loaded) => {
                if (!active) return;
                result = loaded;
                status = 'ready';
            },
            () => {
                if (active) status = 'error';
            }
        );
        // Ignore late results after navigation, size changes, or unmounting.
        return () => {
            active = false;
        };
    });

    return {
        get result() {
            return result;
        },
        get status() {
            return status;
        },
        get boundaryDataUrl() {
            return boundaryDataUrl;
        }
    };
}
