import { describe, it, expect } from 'vitest';
import { APP_ROUTES } from '$lib/routes';
import { SampleType as SampleTypeValues } from '$lib/api/lightly_studio_local';
import { resolveIsDetailPage, resolveScopeLabel, resolveContextFilter } from './useOperatorContext';
import type { PageContext } from './useOperatorContext';

const BASE_CONTEXT: PageContext = {
    routeId: null,
    collectionId: 'coll-1',
    sampleId: null,
    annotationId: null,
    sampleType: null
};

describe('resolveIsDetailPage', () => {
    it('returns false for null', () => {
        expect(resolveIsDetailPage(null)).toBe(false);
    });

    it('returns false for unknown route', () => {
        expect(resolveIsDetailPage('/unknown')).toBe(false);
    });

    it('returns false for collection routes', () => {
        expect(resolveIsDetailPage(APP_ROUTES.images)).toBe(false);
        expect(resolveIsDetailPage(APP_ROUTES.videos)).toBe(false);
        expect(resolveIsDetailPage(APP_ROUTES.frames)).toBe(false);
        expect(resolveIsDetailPage(APP_ROUTES.annotations)).toBe(false);
        expect(resolveIsDetailPage(APP_ROUTES.groups)).toBe(false);
        expect(resolveIsDetailPage(APP_ROUTES.captions)).toBe(false);
    });

    it('returns true for sample detail', () => {
        expect(resolveIsDetailPage(APP_ROUTES.imageDetails)).toBe(true);
    });

    it('returns true for frame detail', () => {
        expect(resolveIsDetailPage(APP_ROUTES.framesDetails)).toBe(true);
    });

    it('returns true for video detail', () => {
        expect(resolveIsDetailPage(APP_ROUTES.videoDetails)).toBe(true);
    });

    it('returns true for annotation detail', () => {
        expect(resolveIsDetailPage(APP_ROUTES.annotationDetails)).toBe(true);
    });
});

describe('resolveScopeLabel', () => {
    it('returns "Full collection" for null sampleType', () => {
        expect(resolveScopeLabel(null, false)).toBe('Full collection');
        expect(resolveScopeLabel(null, true)).toBe('Full collection');
    });

    it('returns detail label when isOnDetailPage is true', () => {
        expect(resolveScopeLabel(SampleTypeValues.IMAGE, true)).toBe('Current image');
        expect(resolveScopeLabel(SampleTypeValues.VIDEO, true)).toBe('Current video');
        expect(resolveScopeLabel(SampleTypeValues.VIDEO_FRAME, true)).toBe('Current video frame');
        expect(resolveScopeLabel(SampleTypeValues.ANNOTATION, true)).toBe('Current annotation');
    });

    it('returns collection label when isOnDetailPage is false', () => {
        expect(resolveScopeLabel(SampleTypeValues.IMAGE, false)).toBe('All images in the view');
        expect(resolveScopeLabel(SampleTypeValues.VIDEO, false)).toBe('All videos in the view');
        expect(resolveScopeLabel(SampleTypeValues.VIDEO_FRAME, false)).toBe(
            'All video frames in the view'
        );
        expect(resolveScopeLabel(SampleTypeValues.ANNOTATION, false)).toBe(
            'All annotations in the view'
        );
        expect(resolveScopeLabel(SampleTypeValues.GROUP, false)).toBe('All groups in the view');
        expect(resolveScopeLabel(SampleTypeValues.CAPTION, false)).toBe('All captions in the view');
    });
});

describe('resolveContextFilter', () => {
    describe('annotation detail route', () => {
        it('returns annotationId as sample_ids when annotationId is present', () => {
            const ctx = {
                ...BASE_CONTEXT,
                routeId: APP_ROUTES.annotationDetails,
                annotationId: 'ann-1'
            };
            expect(resolveContextFilter(ctx, null, null, null, new Set(), new Set())).toEqual({
                sample_ids: ['ann-1']
            });
        });

        it('falls through to sampleId when annotationId is absent', () => {
            const ctx = {
                ...BASE_CONTEXT,
                routeId: APP_ROUTES.annotationDetails,
                sampleId: 'smp-1'
            };
            expect(resolveContextFilter(ctx, null, null, null, new Set(), new Set())).toEqual({
                sample_ids: ['smp-1']
            });
        });
    });

    describe('other detail routes', () => {
        it('returns sampleId as sample_ids on sample detail', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.imageDetails, sampleId: 'smp-1' };
            expect(resolveContextFilter(ctx, null, null, null, new Set(), new Set())).toEqual({
                sample_ids: ['smp-1']
            });
        });

        it('returns sampleId as sample_ids on frame detail', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.framesDetails, sampleId: 'frm-1' };
            expect(resolveContextFilter(ctx, null, null, null, new Set(), new Set())).toEqual({
                sample_ids: ['frm-1']
            });
        });

        it('returns sampleId as sample_ids on video detail', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.videoDetails, sampleId: 'vid-1' };
            expect(resolveContextFilter(ctx, null, null, null, new Set(), new Set())).toEqual({
                sample_ids: ['vid-1']
            });
        });

        it('returns undefined when sampleId is absent on detail page', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.imageDetails };
            expect(
                resolveContextFilter(ctx, null, null, null, new Set(), new Set())
            ).toBeUndefined();
        });
    });

    describe('annotations route', () => {
        it('returns AnnotationsFilter with label_ids when annotationFilterIds is set', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.annotations };
            expect(
                resolveContextFilter(ctx, null, null, null, new Set(['lbl-1', 'lbl-2']), new Set())
            ).toEqual({ annotation_label_ids: ['lbl-1', 'lbl-2'] });
        });

        it('returns AnnotationsFilter with tag_ids when tagsSelected is set', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.annotations };
            expect(
                resolveContextFilter(ctx, null, null, null, new Set(), new Set(['tag-1']))
            ).toEqual({ tag_ids: ['tag-1'] });
        });

        it('returns AnnotationsFilter with both when both are set', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.annotations };
            expect(
                resolveContextFilter(ctx, null, null, null, new Set(['lbl-1']), new Set(['tag-1']))
            ).toEqual({ annotation_label_ids: ['lbl-1'], tag_ids: ['tag-1'] });
        });

        it('returns undefined when no filters are set', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.annotations };
            expect(
                resolveContextFilter(ctx, null, null, null, new Set(), new Set())
            ).toBeUndefined();
        });
    });

    describe('captions route', () => {
        it('returns has_captions filter', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.captions };
            expect(resolveContextFilter(ctx, null, null, null, new Set(), new Set())).toEqual({
                has_captions: true
            });
        });
    });

    describe('collection routes with route-specific filters', () => {
        const imageFilter = { sample_filter: {} };
        const videoFilter = { sample_filter: {} };
        const frameFilter = { sample_filter: {} };

        it('returns imageFilter for samples route', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.images };
            expect(resolveContextFilter(ctx, imageFilter, null, null, new Set(), new Set())).toBe(
                imageFilter
            );
        });

        it('returns undefined when imageFilter is null on samples route', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.images };
            expect(
                resolveContextFilter(ctx, null, null, null, new Set(), new Set())
            ).toBeUndefined();
        });

        it('returns videoFilter for videos route', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.videos };
            expect(resolveContextFilter(ctx, null, videoFilter, null, new Set(), new Set())).toBe(
                videoFilter
            );
        });

        it('returns frameFilter for frames route', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.frames };
            expect(resolveContextFilter(ctx, null, null, frameFilter, new Set(), new Set())).toBe(
                frameFilter
            );
        });
    });

    describe('unknown route', () => {
        it('returns undefined', () => {
            const ctx = { ...BASE_CONTEXT, routeId: '/unknown' };
            expect(
                resolveContextFilter(ctx, null, null, null, new Set(), new Set())
            ).toBeUndefined();
        });

        it('returns undefined for null route', () => {
            expect(
                resolveContextFilter(BASE_CONTEXT, null, null, null, new Set(), new Set())
            ).toBeUndefined();
        });
    });
});
