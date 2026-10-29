import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { useOpenSample } from './useOpenSample';

describe('useOpenSample', () => {
    it('remembers the open sample per tab until the tab forgets it', () => {
        const { openSampleHrefs, rememberOpenSample, forgetOpenSample } = useOpenSample();

        rememberOpenSample('images', '/images/sample-1');
        rememberOpenSample('annotations', '/annotations/annotation-1');
        rememberOpenSample('images', '/images/sample-2');
        expect(get(openSampleHrefs)).toEqual({
            images: '/images/sample-2',
            annotations: '/annotations/annotation-1'
        });

        forgetOpenSample('images');
        expect(get(openSampleHrefs)).toEqual({ annotations: '/annotations/annotation-1' });
    });
});
