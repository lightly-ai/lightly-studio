import { beforeEach, describe, expect, it, vi } from 'vitest';
import { predictAnnotationClasses } from '$lib/api/lightly_studio_local';
import { createAnnotationClassPrediction } from './useAnnotationClassPrediction.svelte';

vi.mock('$lib/api/lightly_studio_local', () => ({
    predictAnnotationClasses: vi.fn()
}));

const prediction = (label_name: string, score: number) => ({
    annotation_label_id: `id-${label_name}`,
    label_name,
    score
});

const respondWith = (data: unknown) =>
    ({ data, error: undefined }) as unknown as Awaited<ReturnType<typeof predictAnnotationClasses>>;

describe('createAnnotationClassPrediction', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('goes loading → ready with the top 3 of the response', async () => {
        const response = [
            prediction('car', 0.6),
            prediction('truck', 0.2),
            prediction('bus', 0.15),
            prediction('bike', 0.05)
        ];
        let resolve: (value: ReturnType<typeof respondWith>) => void = () => {};
        vi.mocked(predictAnnotationClasses).mockReturnValue(
            new Promise((r) => {
                resolve = r;
            }) as ReturnType<typeof predictAnnotationClasses>
        );
        const classPrediction = createAnnotationClassPrediction();

        const pending = classPrediction.predict({ collectionId: 'col', annotationId: 'a' });
        expect(classPrediction.state).toEqual({ status: 'loading', annotationId: 'a' });
        resolve(respondWith(response));
        await pending;

        expect(classPrediction.state).toEqual({
            status: 'ready',
            annotationId: 'a',
            top: response.slice(0, 3)
        });
        expect(predictAnnotationClasses).toHaveBeenCalledWith({
            path: { collection_id: 'col', annotation_id: 'a' }
        });
    });

    it('hides when the response is empty', async () => {
        vi.mocked(predictAnnotationClasses).mockResolvedValue(respondWith([]));
        const classPrediction = createAnnotationClassPrediction();

        await classPrediction.predict({ collectionId: 'col', annotationId: 'a' });

        expect(classPrediction.state).toEqual({ status: 'hidden' });
    });

    it('hides when every score is 0', async () => {
        vi.mocked(predictAnnotationClasses).mockResolvedValue(
            respondWith([prediction('car', 0), prediction('bus', 0)])
        );
        const classPrediction = createAnnotationClassPrediction();

        await classPrediction.predict({ collectionId: 'col', annotationId: 'a' });

        expect(classPrediction.state).toEqual({ status: 'hidden' });
    });

    it('hides on a request error, including 404', async () => {
        vi.mocked(predictAnnotationClasses).mockResolvedValueOnce({
            data: undefined,
            error: { error: 'Annotation not found.' },
            response: { status: 404 }
        } as unknown as Awaited<ReturnType<typeof predictAnnotationClasses>>);
        vi.mocked(predictAnnotationClasses).mockRejectedValueOnce(new Error('network'));
        const classPrediction = createAnnotationClassPrediction();

        await classPrediction.predict({ collectionId: 'col', annotationId: 'a' });
        expect(classPrediction.state).toEqual({ status: 'hidden' });

        await classPrediction.predict({ collectionId: 'col', annotationId: 'b' });
        expect(classPrediction.state).toEqual({ status: 'hidden' });
    });

    it('drops a late response for an older annotation', async () => {
        let resolveA: (value: ReturnType<typeof respondWith>) => void = () => {};
        vi.mocked(predictAnnotationClasses)
            .mockReturnValueOnce(
                new Promise((r) => {
                    resolveA = r;
                }) as ReturnType<typeof predictAnnotationClasses>
            )
            .mockResolvedValueOnce(respondWith([prediction('bus', 1)]));
        const classPrediction = createAnnotationClassPrediction();

        const pendingA = classPrediction.predict({ collectionId: 'col', annotationId: 'a' });
        await classPrediction.predict({ collectionId: 'col', annotationId: 'b' });
        resolveA(respondWith([prediction('car', 1)]));
        await pendingA;

        expect(classPrediction.state).toEqual({
            status: 'ready',
            annotationId: 'b',
            top: [prediction('bus', 1)]
        });
    });

    it('hide() drops a pending response', async () => {
        let resolve: (value: ReturnType<typeof respondWith>) => void = () => {};
        vi.mocked(predictAnnotationClasses).mockReturnValue(
            new Promise((r) => {
                resolve = r;
            }) as ReturnType<typeof predictAnnotationClasses>
        );
        const classPrediction = createAnnotationClassPrediction();

        const pending = classPrediction.predict({ collectionId: 'col', annotationId: 'a' });
        classPrediction.hide();
        resolve(respondWith([prediction('car', 1)]));
        await pending;

        expect(classPrediction.state).toEqual({ status: 'hidden' });
    });
});
