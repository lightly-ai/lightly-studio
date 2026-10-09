import { describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import OriginAxes from './OriginAxes.svelte';

const { axesHelper } = vi.hoisted(() => ({ axesHelper: vi.fn() }));

vi.mock('@threlte/core', () => ({
    T: { AxesHelper: axesHelper }
}));

describe('OriginAxes', () => {
    it('renders axes with the default size', () => {
        render(OriginAxes);
        expect(axesHelper.mock.calls.at(-1)?.[1].args).toEqual([3]);
    });

    it('renders axes with a custom size', () => {
        render(OriginAxes, { props: { size: 10 } });
        expect(axesHelper.mock.calls.at(-1)?.[1].args).toEqual([10]);
    });
});
