import { describe, expect, it } from 'vitest';
import { APP_ROUTES } from '$lib/routes';
import { isAssistedLabelingView } from './isAssistedLabelingView';

describe('isAssistedLabelingView', () => {
    it('is true on the image details view', () => {
        expect(
            isAssistedLabelingView({
                isOnAnnotationDetailsView: false,
                routeId: APP_ROUTES.imageDetails
            })
        ).toBe(true);
    });

    it('is false on the frame details view', () => {
        expect(
            isAssistedLabelingView({
                isOnAnnotationDetailsView: false,
                routeId: APP_ROUTES.framesDetails
            })
        ).toBe(false);
    });

    it('is false on the annotation details view', () => {
        expect(
            isAssistedLabelingView({
                isOnAnnotationDetailsView: true,
                routeId: APP_ROUTES.imageDetails
            })
        ).toBe(false);
    });
});
