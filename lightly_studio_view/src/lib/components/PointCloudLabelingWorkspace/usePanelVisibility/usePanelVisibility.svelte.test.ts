import { flushSync } from 'svelte';
import { afterEach, expect, it } from 'vitest';
import { usePanelVisibility } from './usePanelVisibility.svelte';

const storageKey = 'lightlyStudio_pointCloudTestPanelVisible';
let dispose = () => {};
afterEach(() => {
    dispose();
    sessionStorage.removeItem(storageKey);
});

const setup = (defaultVisible: boolean) => {
    let hook!: ReturnType<typeof usePanelVisibility>;
    dispose = $effect.root(() => {
        hook = usePanelVisibility(storageKey, defaultVisible);
    });
    flushSync();
    return hook;
};

it('starts with the default and remembers toggles for the next load', () => {
    const hook = setup(false);
    expect(hook.visible).toBe(false);

    hook.toggle();
    flushSync();
    expect(hook.visible).toBe(true);
    expect(sessionStorage.getItem(storageKey)).toBe('true');

    dispose();
    expect(setup(false).visible).toBe(true);
});

it('hides a shown panel', () => {
    const hook = setup(true);

    hook.setVisible(false);
    flushSync();

    expect(hook.visible).toBe(false);
});
