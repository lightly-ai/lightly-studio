import type { PortalProps } from 'bits-ui';
import { getContext, hasContext, setContext } from 'svelte';

/** Element or selector that receives portaled dialogs, popovers, and selects. */
export type PortalTarget = NonNullable<PortalProps['to']>;

const PORTAL_TARGET_KEY = Symbol('portal-target');

const getBodyPortalTarget = (): PortalTarget => 'body';

/**
 * Sets the portal target for the component subtree.
 *
 * A browser in fullscreen shows only the fullscreen element, so content portaled to <body>
 * is not visible. A fullscreen container gives itself as the target.
 */
export function providePortalTarget(getTarget: () => PortalTarget): void {
    setContext(PORTAL_TARGET_KEY, getTarget);
}

/** Returns a getter for the nearest portal target. The default target is <body>. */
export function usePortalTarget(): () => PortalTarget {
    if (!hasContext(PORTAL_TARGET_KEY)) return getBodyPortalTarget;
    return getContext<() => PortalTarget>(PORTAL_TARGET_KEY);
}
