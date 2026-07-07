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

    it('returns true for image detail', () => {
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
    it('returns entire-collection fragment for null sampleType regardless of count or filter', () => {
        expect(resolveScopeLabel(null, false, 100, false)).toBe('the entire collection');
        expect(resolveScopeLabel(null, true, 1, true)).toBe('the entire collection');
    });

    it('returns currently-viewed fragment when isOnDetailPage is true', () => {
        expect(resolveScopeLabel(SampleTypeValues.IMAGE, true, 1, false)).toBe(
            'the currently viewed image'
        );
        expect(resolveScopeLabel(SampleTypeValues.VIDEO, true, 1, false)).toBe(
            'the currently viewed video'
        );
        expect(resolveScopeLabel(SampleTypeValues.VIDEO_FRAME, true, 1, false)).toBe(
            'the currently viewed video frame'
        );
        expect(resolveScopeLabel(SampleTypeValues.ANNOTATION, true, 1, false)).toBe(
            'the currently viewed annotation'
        );
    });

    it('returns "all {count} {type}s" when no filter is active', () => {
        expect(resolveScopeLabel(SampleTypeValues.IMAGE, false, 1204, false)).toBe(
            'all 1204 images'
        );
        expect(resolveScopeLabel(SampleTypeValues.VIDEO, false, 42, false)).toBe('all 42 videos');
        expect(resolveScopeLabel(SampleTypeValues.VIDEO_FRAME, false, 50, false)).toBe(
            'all 50 video frames'
        );
        expect(resolveScopeLabel(SampleTypeValues.ANNOTATION, false, 30, false)).toBe(
            'all 30 annotations'
        );
        expect(resolveScopeLabel(SampleTypeValues.GROUP, false, 10, false)).toBe('all 10 groups');
        expect(resolveScopeLabel(SampleTypeValues.CAPTION, false, 5, false)).toBe('all 5 captions');
    });

    it('returns "{count} filtered {type}s" when a filter is active', () => {
        expect(resolveScopeLabel(SampleTypeValues.IMAGE, false, 248, true)).toBe(
            '248 filtered images'
        );
        expect(resolveScopeLabel(SampleTypeValues.VIDEO, false, 3, true)).toBe('3 filtered videos');
        expect(resolveScopeLabel(SampleTypeValues.VIDEO_FRAME, false, 20, true)).toBe(
            '20 filtered video frames'
        );
        expect(resolveScopeLabel(SampleTypeValues.ANNOTATION, false, 12, true)).toBe(
            '12 filtered annotations'
        );
    });

    it('uses singular form when scopeCount is 1', () => {
        expect(resolveScopeLabel(SampleTypeValues.IMAGE, false, 1, false)).toBe('all 1 image');
        expect(resolveScopeLabel(SampleTypeValues.VIDEO, false, 1, false)).toBe('all 1 video');
        expect(resolveScopeLabel(SampleTypeValues.IMAGE, false, 1, true)).toBe('1 filtered image');
        expect(resolveScopeLabel(SampleTypeValues.VIDEO_FRAME, false, 1, true)).toBe(
            '1 filtered video frame'
        );
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
                filter_type: 'sample',
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
                filter_type: 'sample',
                sample_ids: ['smp-1']
            });
        });
    });

    describe('other detail routes', () => {
        it('returns sampleId as sample_ids on image detail', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.imageDetails, sampleId: 'smp-1' };
            expect(resolveContextFilter(ctx, null, null, null, new Set(), new Set())).toEqual({
                filter_type: 'sample',
                sample_ids: ['smp-1']
            });
        });

        it('returns sampleId as sample_ids on frame detail', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.framesDetails, sampleId: 'frm-1' };
            expect(resolveContextFilter(ctx, null, null, null, new Set(), new Set())).toEqual({
                filter_type: 'sample',
                sample_ids: ['frm-1']
            });
        });

        it('returns sampleId as sample_ids on video detail', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.videoDetails, sampleId: 'vid-1' };
            expect(resolveContextFilter(ctx, null, null, null, new Set(), new Set())).toEqual({
                filter_type: 'sample',
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
            ).toEqual({ filter_type: 'annotations', annotation_label_ids: ['lbl-1', 'lbl-2'] });
        });

        it('returns AnnotationsFilter with tag_ids when tagsSelected is set', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.annotations };
            expect(
                resolveContextFilter(ctx, null, null, null, new Set(), new Set(['tag-1']))
            ).toEqual({ filter_type: 'annotations', tag_ids: ['tag-1'] });
        });

        it('returns AnnotationsFilter with both when both are set', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.annotations };
            expect(
                resolveContextFilter(ctx, null, null, null, new Set(['lbl-1']), new Set(['tag-1']))
            ).toEqual({
                filter_type: 'annotations',
                annotation_label_ids: ['lbl-1'],
                tag_ids: ['tag-1']
            });
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
                filter_type: 'sample',
                has_captions: true
            });
        });
    });

    describe('collection routes with route-specific filters', () => {
        const imageFilter = { sample_filter: {} };
        const videoFilter = { sample_filter: {} };
        const frameFilter = { sample_filter: {} };

        it('returns imageFilter with filter_type for images route', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.images };
            expect(
                resolveContextFilter(ctx, imageFilter, null, null, new Set(), new Set())
            ).toEqual({ ...imageFilter, filter_type: 'image' });
        });

        it('returns undefined when imageFilter is null on images route', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.images };
            expect(
                resolveContextFilter(ctx, null, null, null, new Set(), new Set())
            ).toBeUndefined();
        });

        it('returns videoFilter with filter_type for videos route', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.videos };
            expect(
                resolveContextFilter(ctx, null, videoFilter, null, new Set(), new Set())
            ).toEqual({ ...videoFilter, filter_type: 'video' });
        });

        it('returns frameFilter with filter_type for frames route', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.frames };
            expect(
                resolveContextFilter(ctx, null, null, frameFilter, new Set(), new Set())
            ).toEqual({ ...frameFilter, filter_type: 'video_frame' });
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
