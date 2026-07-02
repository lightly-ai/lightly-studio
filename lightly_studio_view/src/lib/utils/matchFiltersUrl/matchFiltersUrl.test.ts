import { describe, expect, it } from 'vitest';
import { EvaluationMatchType } from '$lib/api/lightly_studio_local';
import {
    parseConfusionCellParam,
    parseMatchTypesParam,
    setConfusionCellInUrl,
    toggleMatchTypeInUrl
} from './matchFiltersUrl';

const BASE = 'http://localhost/datasets/ds/annotation/col/evaluation/run-1/matches';
const urlWith = (query: string): URL => new URL(query ? `${BASE}?${query}` : BASE);

describe('parseMatchTypesParam', () => {
    it('returns an empty array when the param is absent', () => {
        expect(parseMatchTypesParam(urlWith('').searchParams)).toEqual([]);
    });

    it('parses a comma-separated list, dropping unknown values', () => {
        expect(parseMatchTypesParam(urlWith('match_types=tp,fp,bogus').searchParams)).toEqual([
            EvaluationMatchType.TP,
            EvaluationMatchType.FP
        ]);
    });
});

describe('parseConfusionCellParam', () => {
    it('returns undefined when neither label param is present', () => {
        expect(parseConfusionCellParam(urlWith('').searchParams, 'run-1')).toBeUndefined();
    });

    it('reads a class-by-class cell', () => {
        expect(
            parseConfusionCellParam(urlWith('cc_gt=cat&cc_pred=dog').searchParams, 'run-1')
        ).toEqual({ evaluation_run_id: 'run-1', gt_label: 'cat', pred_label: 'dog' });
    });

    it('maps a missing gt param to the false-positive bucket (null gt_label)', () => {
        expect(parseConfusionCellParam(urlWith('cc_pred=dog').searchParams, 'run-1')).toEqual({
            evaluation_run_id: 'run-1',
            gt_label: null,
            pred_label: 'dog'
        });
    });

    it('maps a missing pred param to the false-negative bucket (null pred_label)', () => {
        expect(parseConfusionCellParam(urlWith('cc_gt=cat').searchParams, 'run-1')).toEqual({
            evaluation_run_id: 'run-1',
            gt_label: 'cat',
            pred_label: null
        });
    });
});

describe('setConfusionCellInUrl', () => {
    it('adds both label params while preserving other filters', () => {
        const result = setConfusionCellInUrl(urlWith('sample_ids=a,b'), {
            evaluation_run_id: 'run-1',
            gt_label: 'cat',
            pred_label: 'dog'
        });
        const params = new URL(result, BASE).searchParams;
        expect(params.get('sample_ids')).toBe('a,b');
        expect(params.get('cc_gt')).toBe('cat');
        expect(params.get('cc_pred')).toBe('dog');
    });

    it('omits the null side of a margin bucket', () => {
        const result = setConfusionCellInUrl(urlWith(''), {
            evaluation_run_id: 'run-1',
            gt_label: null,
            pred_label: 'dog'
        });
        const params = new URL(result, BASE).searchParams;
        expect(params.has('cc_gt')).toBe(false);
        expect(params.get('cc_pred')).toBe('dog');
    });

    it('clears both label params when passed null', () => {
        const result = setConfusionCellInUrl(urlWith('cc_gt=cat&cc_pred=dog&match_types=tp'), null);
        const params = new URL(result, BASE).searchParams;
        expect(params.has('cc_gt')).toBe(false);
        expect(params.has('cc_pred')).toBe(false);
        expect(params.get('match_types')).toBe('tp');
    });
});

describe('toggleMatchTypeInUrl', () => {
    it('adds a match type when not present', () => {
        const result = toggleMatchTypeInUrl(urlWith(''), EvaluationMatchType.TP);
        expect(new URL(result, BASE).searchParams.get('match_types')).toBe('tp');
    });

    it('removes a match type when already present', () => {
        const result = toggleMatchTypeInUrl(urlWith('match_types=tp,fp'), EvaluationMatchType.TP);
        expect(new URL(result, BASE).searchParams.get('match_types')).toBe('fp');
    });

    it('drops the param entirely when the last type is removed', () => {
        const result = toggleMatchTypeInUrl(urlWith('match_types=tp'), EvaluationMatchType.TP);
        expect(new URL(result, BASE).searchParams.has('match_types')).toBe(false);
    });
});
