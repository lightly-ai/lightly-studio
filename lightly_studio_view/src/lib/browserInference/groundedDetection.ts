import type { ModelAnnotationPreview } from '$lib/api/lightly_studio_local';

interface Span {
    start: number;
    end: number;
}

interface DecodeGroundedDetectionsParams {
    // Shape [queries, numTokens]: the logit of each query for each text token.
    logits: Float32Array;
    // Shape [queries, 4]: normalized cxcywh boxes.
    boxes: Float32Array;
    numTokens: number;
    // The token range of each class name in the prompt, in the order of classNames.
    spans: Span[];
    classNames: string[];
    imageWidth: number;
    imageHeight: number;
    threshold: number;
}

const BOX_VALUES = 4;

// Finds the tokens of each phrase in a Grounding DINO prompt like "forklift. pallet.".
export const toPhraseSpans = (
    inputIds: number[],
    tokens: { specialIds: Set<number>; separatorId: number }
): Span[] => {
    const spans: Span[] = [];
    let start: number | null = null;
    inputIds.forEach((id, index) => {
        const isPhraseEnd = id === tokens.separatorId || tokens.specialIds.has(id);
        if (isPhraseEnd && start !== null) {
            spans.push({ start, end: index });
            start = null;
        } else if (!isPhraseEnd && start === null) {
            start = index;
        }
    });
    return spans;
};

// Mirrors Grounding DINO post-processing: a query's score for a class is its best token in
// that class name, and the query keeps its best class.
export const decodeGroundedDetections = (
    params: DecodeGroundedDetectionsParams
): ModelAnnotationPreview[] => {
    const queryCount = params.boxes.length / BOX_VALUES;
    const previews: ModelAnnotationPreview[] = [];
    for (let query = 0; query < queryCount; query++) {
        const best = findBestClass(params, query);
        if (best.score > params.threshold) {
            previews.push(toPreview({ params, query, ...best }));
        }
    }
    return previews.sort((a, b) => b.score - a.score);
};

const findBestClass = (params: DecodeGroundedDetectionsParams, query: number) => {
    let best = { classIndex: -1, score: 0 };
    params.spans.forEach(({ start, end }, classIndex) => {
        for (let token = start; token < end; token++) {
            const score = sigmoid(params.logits[query * params.numTokens + token]);
            if (score > best.score) best = { classIndex, score };
        }
    });
    return best;
};

const toPreview = ({
    params,
    query,
    classIndex,
    score
}: {
    params: DecodeGroundedDetectionsParams;
    query: number;
    classIndex: number;
    score: number;
}): ModelAnnotationPreview => {
    const offset = query * BOX_VALUES;
    const [centerX, centerY, boxWidth, boxHeight] = params.boxes.subarray(
        offset,
        offset + BOX_VALUES
    );
    const left = Math.round((centerX - boxWidth / 2) * params.imageWidth);
    const top = Math.round((centerY - boxHeight / 2) * params.imageHeight);
    const right = Math.round((centerX + boxWidth / 2) * params.imageWidth);
    const bottom = Math.round((centerY + boxHeight / 2) * params.imageHeight);
    return {
        class_name: params.classNames[classIndex],
        bbox: { x: left, y: top, width: right - left, height: bottom - top },
        segmentation_mask: null,
        score
    };
};

const sigmoid = (logit: number) => 1 / (1 + Math.exp(-logit));
