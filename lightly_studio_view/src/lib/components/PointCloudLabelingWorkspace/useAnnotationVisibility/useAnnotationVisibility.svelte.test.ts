import { flushSync } from 'svelte';
import { afterEach, describe, expect, it } from 'vitest';
import { createCuboidAnnotation } from '../domain';
import { createAnnotationFixture } from '../domain/fixtures';
import { useAnnotationVisibility } from './useAnnotationVisibility.svelte';

const cuboid = createAnnotationFixture();
const sameTrackNextTick = createCuboidAnnotation({ ...cuboid, id: 'annotation-1' });
const otherTrack = createCuboidAnnotation({ ...cuboid, id: 'annotation-2', trackId: 'track-1' });

let dispose = () => {};
afterEach(() => dispose());

function setup() {
    let resetKey = $state('sequence-1');
    let hook!: ReturnType<typeof useAnnotationVisibility>;
    dispose = $effect.root(() => {
        hook = useAnnotationVisibility(() => resetKey);
    });
    flushSync();
    return {
        hook,
        setResetKey: (key: string) => {
            resetKey = key;
            flushSync();
        }
    };
}

describe('useAnnotationVisibility', () => {
    it('hides a track and shows it again on a second toggle', () => {
        const { hook } = setup();

        hook.toggleTrack(cuboid);
        expect(hook.isCuboidHidden(sameTrackNextTick)).toBe(true);
        expect(hook.isCuboidHidden(otherTrack)).toBe(false);

        hook.toggleTrack(cuboid);
        expect(hook.isCuboidHidden(sameTrackNextTick)).toBe(false);
    });

    it('hides every cuboid of a toggled source', () => {
        const { hook } = setup();

        hook.toggleSource('ground-truth');

        expect(hook.isSourceHidden('ground-truth')).toBe(true);
        expect(hook.isCuboidHidden(cuboid)).toBe(true);
        expect(hook.isCuboidHidden(otherTrack)).toBe(true);
    });

    it('shows everything again when the reset key changes', () => {
        const { hook, setResetKey } = setup();
        hook.toggleTrack(cuboid);
        hook.toggleSource('predictions');

        setResetKey('sequence-2');

        expect(hook.isCuboidHidden(cuboid)).toBe(false);
        expect(hook.isSourceHidden('predictions')).toBe(false);
    });
});
