import type { SuperpixelMaskEditor } from '@lightly-ai/slic';
import { maskToDataUrl } from '$lib/components/SampleAnnotation/utils';
import parseColor from '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/parseColor';

interface PreviewProps {
    width: number;
    height: number;
    color: string;
}

export function useSlicPreview(getProps: () => PreviewProps) {
    let hoverMaskDataUrl = $state('');
    let strokeMaskDataUrl = $state('');
    let hoveredLabel: number | null = null;

    const renderMask = (mask: Uint8Array) => {
        const { width, height, color } = getProps();
        // Translucent previews keep the underlying image visible.
        return maskToDataUrl(mask, width, height, { ...parseColor(color), a: 85 });
    };
    return {
        get hoverMaskDataUrl() {
            return hoverMaskDataUrl;
        },
        get strokeMaskDataUrl() {
            return strokeMaskDataUrl;
        },
        updateHover(point: { x: number; y: number }, editor: SuperpixelMaskEditor) {
            const label = editor.getLabelAtPoint(point);
            if (label === hoveredLabel) return;
            hoveredLabel = label;
            hoverMaskDataUrl = renderMask(editor.getSegmentPreviewMask(label));
        },
        renderStroke(mask: Uint8Array) {
            strokeMaskDataUrl = renderMask(mask);
        },
        clearStroke() {
            strokeMaskDataUrl = '';
        },
        clear() {
            hoveredLabel = null;
            hoverMaskDataUrl = '';
            strokeMaskDataUrl = '';
        }
    };
}
