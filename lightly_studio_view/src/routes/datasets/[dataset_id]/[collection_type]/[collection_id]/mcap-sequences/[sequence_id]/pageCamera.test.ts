import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { afterNavigate, goto } from '$app/navigation';
import Page from './+page.svelte';
import type { PageData } from './$types';

interface WorkspaceProps {
    tickNumber: number;
    openCamera?: string;
    onTickChange: (tick: number) => void;
    onOpenCameraChange: (camera: string | undefined, historyMode: 'push' | 'replace') => void;
}

const workspace = vi.hoisted(() => ({ props: undefined as unknown }));
const routePage = vi.hoisted(() => ({
    url: new URL('http://localhost/datasets/d/mcap/c/mcap-sequences/s'),
    params: { dataset_id: 'dataset-1' },
    state: {}
}));

vi.mock('$app/navigation', () => ({ goto: vi.fn(), afterNavigate: vi.fn() }));
vi.mock('$app/state', () => ({ page: routePage }));
vi.mock('$lib/hooks', () => ({
    useMcapSequenceSummary: () => ({ summary: { data: undefined } })
}));
vi.mock('$lib/hooks/useAdjacentMcapSequences/useAdjacentMcapSequences', () => ({
    useAdjacentMcapSequences: () => ({ query: { data: undefined } })
}));
vi.mock('$lib/components', async () => {
    const { default: LayoutCard } = await import('$lib/components/LayoutCard/LayoutCard.svelte');
    return { LayoutCard };
});
vi.mock('$lib/components/PointCloudLabelingWorkspace/PointCloudLabelingWorkspace.svelte', () => ({
    default: (_anchor: unknown, props: unknown) => {
        workspace.props = props;
    }
}));

const data = {
    datasetId: 'dataset-1',
    annotationSourceCollectionId: 'group-1',
    collectionId: 'collection-1',
    collectionName: 'Collection 1',
    collectionType: 'mcap',
    sequenceId: 'sequence-1'
} as unknown as PageData;

const props = () => workspace.props as WorkspaceProps;
const lastGoto = () => {
    const [url, options] = vi.mocked(goto).mock.lastCall!;
    return { hash: (url as URL).hash, options };
};

const popstate = (fromPath: string, toPath: string) => {
    const callback = vi.mocked(afterNavigate).mock.calls[0][0] as (nav: unknown) => void;
    callback({
        type: 'popstate',
        from: { url: new URL(`http://localhost${fromPath}`) },
        to: { url: new URL(`http://localhost${toPath}`) }
    });
};

describe('point-cloud sequence page camera hash', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        routePage.url = new URL('http://localhost/datasets/d/mcap/c/mcap-sequences/s#tick=2');
    });

    it('passes the camera from the hash to the workspace', () => {
        routePage.url = new URL('http://localhost/x#tick=2&camera=CAM_B');
        render(Page, { props: { data } });

        expect(props().openCamera).toBe('CAM_B');
        expect(props().tickNumber).toBe(2);
    });

    it('defaults to the first tick and no camera', () => {
        routePage.url = new URL('http://localhost/x');
        render(Page, { props: { data } });

        expect(props().tickNumber).toBe(1);
        expect(props().openCamera).toBeUndefined();
    });

    it('pushes a history entry when a camera opens', () => {
        render(Page, { props: { data } });

        props().onOpenCameraChange('CAM_B', 'push');

        expect(lastGoto().hash).toBe('#tick=2&camera=CAM_B');
        expect(lastGoto().options).toMatchObject({ replaceState: false, noScroll: true });
    });

    it('replaces the history entry when switching cameras', () => {
        render(Page, { props: { data } });

        props().onOpenCameraChange('CAM_B', 'replace');

        expect(lastGoto().hash).toBe('#tick=2&camera=CAM_B');
        expect(lastGoto().options).toMatchObject({ replaceState: true });
    });

    it('keeps the camera when the tick changes right after a switch', () => {
        render(Page, { props: { data } });

        props().onOpenCameraChange('CAM_C', 'replace');
        props().onTickChange(5);

        expect(lastGoto().hash).toBe('#tick=5&camera=CAM_C');
    });

    it('closing after switches pops a single history entry', () => {
        const back = vi.spyOn(history, 'back').mockImplementation(() => {});
        render(Page, { props: { data } });

        props().onOpenCameraChange('CAM_A', 'push');
        props().onOpenCameraChange('CAM_B', 'replace');
        props().onOpenCameraChange('CAM_C', 'replace');
        vi.mocked(goto).mockClear();
        props().onOpenCameraChange(undefined, 'replace');

        expect(back).toHaveBeenCalledOnce();
        expect(goto).not.toHaveBeenCalled();
        back.mockRestore();
    });

    it('closes a camera from the initial URL by replacing the hash', () => {
        routePage.url = new URL('http://localhost/x#tick=2&camera=CAM_B');
        const back = vi.spyOn(history, 'back').mockImplementation(() => {});
        render(Page, { props: { data } });

        props().onOpenCameraChange(undefined, 'replace');

        expect(back).not.toHaveBeenCalled();
        expect(lastGoto().hash).toBe('#tick=2');
        expect(lastGoto().options).toMatchObject({ replaceState: true });
        back.mockRestore();
    });

    it('syncs the camera and tick from the URL after a popstate navigation', () => {
        render(Page, { props: { data } });
        props().onOpenCameraChange('CAM_A', 'push');
        routePage.url = new URL('http://localhost/other#tick=7');
        popstate('/x', '/other');

        expect(props().openCamera).toBeUndefined();
        expect(props().tickNumber).toBe(7);
    });

    it('keeps the live tick when closing lands on the stale open-time entry', () => {
        vi.spyOn(history, 'back').mockImplementation(() => {});
        render(Page, { props: { data } });
        props().onOpenCameraChange('CAM_A', 'push');
        props().onTickChange(9);
        props().onOpenCameraChange(undefined, 'replace');

        routePage.url = new URL('http://localhost/datasets/d/mcap/c/mcap-sequences/s#tick=2');
        popstate('/same', '/same');

        expect(props().tickNumber).toBe(9);
        expect(props().openCamera).toBeUndefined();
        expect(lastGoto().hash).toBe('#tick=9');
        expect(lastGoto().options).toMatchObject({ replaceState: true });
    });

    it('defers tick writes while history.back is pending', () => {
        vi.spyOn(history, 'back').mockImplementation(() => {});
        render(Page, { props: { data } });
        props().onOpenCameraChange('CAM_A', 'push');
        props().onOpenCameraChange(undefined, 'replace');
        vi.mocked(goto).mockClear();

        props().onTickChange(10);
        expect(goto).not.toHaveBeenCalled();

        routePage.url = new URL('http://localhost/datasets/d/mcap/c/mcap-sequences/s#tick=2');
        popstate('/same', '/same');

        expect(goto).toHaveBeenCalledOnce();
        expect(lastGoto().hash).toBe('#tick=10');
    });
});
