import { getContext, setContext } from 'svelte';
import { writable, type Writable } from 'svelte/store';

const CONTEXT_KEY = Symbol('active-point-cloud-viewport');

export function provideActiveViewportContext(): void {
    setContext(CONTEXT_KEY, writable<symbol | null>(null));
}

export function useActiveViewportContext(): Writable<symbol | null> {
    return getContext<Writable<symbol | null>>(CONTEXT_KEY) ?? writable<symbol | null>(null);
}
