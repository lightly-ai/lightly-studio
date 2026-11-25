import type { BoundingBox } from '$lib/types';
import { isSamePlacement, placeCard } from './cardPlacement';
import { followLayer } from './followLayer';

interface Params {
    /** The annotation's rectangle in image coordinates. */
    bbox: BoundingBox;
    /** The annotation layer of the canvas, whose screen matrix includes pan and zoom. */
    layer: SVGGraphicsElement | null;
    card: HTMLElement | undefined;
}

/**
 * Where the card sits on screen, beside the box. It follows the box: pan, zoom, resizes and
 * edits of the box all move it. Null until the card is placed and while the layer or the card
 * is missing. Call during component init.
 */
export const useCardPlacement = (getParams: () => Params) => {
    let placement = $state<ReturnType<typeof placeCard> | null>(null);

    const place = (layer: SVGGraphicsElement, card: HTMLElement) => {
        const matrix = layer.getScreenCTM();
        const canvas = layer.ownerSVGElement?.getBoundingClientRect();
        const size = { width: card.offsetWidth, height: card.offsetHeight };
        const { bbox } = getParams();
        const next = matrix && canvas ? placeCard({ bbox, matrix, canvas, card: size }) : null;
        if (!isSamePlacement(placement, next)) placement = next;
    };

    $effect(() => {
        const { bbox, layer, card } = getParams();
        if (!layer || !card) {
            placement = null;
            return;
        }
        void [bbox.x, bbox.y, bbox.width, bbox.height];
        return followLayer(layer, card, () => place(layer, card));
    });

    return {
        get current() {
            return placement;
        }
    };
};
