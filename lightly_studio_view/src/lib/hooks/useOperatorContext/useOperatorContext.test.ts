import { describe, it, expect } from 'vitest';
import { OperatorScope as OperatorScopeValues } from '$lib/api/lightly_studio_local';
import { APP_ROUTES } from '$lib/routes';
import {
    resolveIsDetailPage,
    resolveCurrentScope,
    resolveScopeLabel,
    resolveContextFilter
} from './useOperatorContext';
import type { PageContext } from './useOperatorContext';

const BASE_CONTEXT: PageContext = {
    routeId: null,
    collectionId: 'coll-1',
    sampleId: null,
    annotationId: null
};

describe('resolveIsDetailPage', () => {
    it('returns false for null', () => {
        expect(resolveIsDetailPage(null)).toBe(false);
    });

    it('returns false for unknown route', () => {
        expect(resolveIsDetailPage('/unknown')).toBe(false);
    });

    it('returns false for collection routes', () => {
        expect(resolveIsDetailPage(APP_ROUTES.samples)).toBe(false);
        expect(resolveIsDetailPage(APP_ROUTES.videos)).toBe(false);
        expect(resolveIsDetailPage(APP_ROUTES.frames)).toBe(false);
        expect(resolveIsDetailPage(APP_ROUTES.annotations)).toBe(false);
        expect(resolveIsDetailPage(APP_ROUTES.groups)).toBe(false);
        expect(resolveIsDetailPage(APP_ROUTES.captions)).toBe(false);
    });

    it('returns true for sample detail', () => {
        expect(resolveIsDetailPage(APP_ROUTES.sampleDetails)).toBe(true);
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

describe('resolveCurrentScope', () => {
    it('returns null for null route', () => {
        expect(resolveCurrentScope(null)).toBeNull();
    });

    it('returns null for unknown route', () => {
        expect(resolveCurrentScope('/unknown')).toBeNull();
    });

    it('returns IMAGE for samples and sampleDetails', () => {
        expect(resolveCurrentScope(APP_ROUTES.samples)).toBe(OperatorScopeValues.IMAGE);
        expect(resolveCurrentScope(APP_ROUTES.sampleDetails)).toBe(OperatorScopeValues.IMAGE);
    });

    it('returns VIDEO for videos and videoDetails', () => {
        expect(resolveCurrentScope(APP_ROUTES.videos)).toBe(OperatorScopeValues.VIDEO);
        expect(resolveCurrentScope(APP_ROUTES.videoDetails)).toBe(OperatorScopeValues.VIDEO);
    });

    it('returns VIDEO_FRAME for frames and framesDetails', () => {
        expect(resolveCurrentScope(APP_ROUTES.frames)).toBe(OperatorScopeValues.VIDEO_FRAME);
        expect(resolveCurrentScope(APP_ROUTES.framesDetails)).toBe(OperatorScopeValues.VIDEO_FRAME);
    });

    it('returns ANNOTATION for annotations and annotationDetails', () => {
        expect(resolveCurrentScope(APP_ROUTES.annotations)).toBe(OperatorScopeValues.ANNOTATION);
        expect(resolveCurrentScope(APP_ROUTES.annotationDetails)).toBe(
            OperatorScopeValues.ANNOTATION
        );
    });

    it('returns GROUP for groups', () => {
        expect(resolveCurrentScope(APP_ROUTES.groups)).toBe(OperatorScopeValues.GROUP);
    });

    it('returns CAPTION for captions', () => {
        expect(resolveCurrentScope(APP_ROUTES.captions)).toBe(OperatorScopeValues.CAPTION);
    });
});

describe('resolveScopeLabel', () => {
    it('returns "Full collection" for null or unknown route', () => {
        expect(resolveScopeLabel(null)).toBe('Full collection');
        expect(resolveScopeLabel('/unknown')).toBe('Full collection');
    });

    it('returns detail labels for detail routes', () => {
        expect(resolveScopeLabel(APP_ROUTES.sampleDetails)).toBe('Current image');
        expect(resolveScopeLabel(APP_ROUTES.framesDetails)).toBe('Current frame');
        expect(resolveScopeLabel(APP_ROUTES.videoDetails)).toBe('Current video');
        expect(resolveScopeLabel(APP_ROUTES.annotationDetails)).toBe('Current annotation');
    });

    it('returns collection labels for collection routes', () => {
        expect(resolveScopeLabel(APP_ROUTES.samples)).toBe('Current image collection');
        expect(resolveScopeLabel(APP_ROUTES.videos)).toBe('Current video collection');
        expect(resolveScopeLabel(APP_ROUTES.frames)).toBe('Current frame collection');
        expect(resolveScopeLabel(APP_ROUTES.annotations)).toBe('Current annotation collection');
        expect(resolveScopeLabel(APP_ROUTES.groups)).toBe('Current group collection');
        expect(resolveScopeLabel(APP_ROUTES.captions)).toBe('Current caption collection');
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
                collection_id: 'coll-1',
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
                collection_id: 'coll-1',
                sample_ids: ['smp-1']
            });
        });
    });

    describe('other detail routes', () => {
        it('returns sampleId as sample_ids on sample detail', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.sampleDetails, sampleId: 'smp-1' };
            expect(resolveContextFilter(ctx, null, null, null, new Set(), new Set())).toEqual({
                collection_id: 'coll-1',
                sample_ids: ['smp-1']
            });
        });

        it('returns sampleId as sample_ids on frame detail', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.framesDetails, sampleId: 'frm-1' };
            expect(resolveContextFilter(ctx, null, null, null, new Set(), new Set())).toEqual({
                collection_id: 'coll-1',
                sample_ids: ['frm-1']
            });
        });

        it('returns sampleId as sample_ids on video detail', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.videoDetails, sampleId: 'vid-1' };
            expect(resolveContextFilter(ctx, null, null, null, new Set(), new Set())).toEqual({
                collection_id: 'coll-1',
                sample_ids: ['vid-1']
            });
        });

        it('returns undefined when sampleId is absent on detail page', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.sampleDetails };
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
            ).toEqual({ annotation_tag_ids: ['tag-1'] });
        });

        it('returns AnnotationsFilter with both when both are set', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.annotations };
            expect(
                resolveContextFilter(ctx, null, null, null, new Set(['lbl-1']), new Set(['tag-1']))
            ).toEqual({ annotation_label_ids: ['lbl-1'], annotation_tag_ids: ['tag-1'] });
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
        const imageFilter = { collection_id: 'coll-1' };
        const videoFilter = { sample_filter: { collection_id: 'coll-1' } };
        const frameFilter = { sample_filter: { collection_id: 'coll-1' } };

        it('returns imageFilter for samples route', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.samples };
            expect(resolveContextFilter(ctx, imageFilter, null, null, new Set(), new Set())).toBe(
                imageFilter
            );
        });

        it('returns undefined when imageFilter is null on samples route', () => {
            const ctx = { ...BASE_CONTEXT, routeId: APP_ROUTES.samples };
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
