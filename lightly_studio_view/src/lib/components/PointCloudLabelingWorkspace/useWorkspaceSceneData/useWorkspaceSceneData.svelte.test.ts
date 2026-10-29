import { flushSync } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local/types.gen';
import type { PointCloudWorkspaceContext } from '../provider/types';
import { useWorkspaceSceneData } from './useWorkspaceSceneData.svelte';

vi.mock('$lib/hooks', () => ({ useAnnotationCollections: () => ({ data: [] }) }));
vi.mock('$lib/hooks/useCustomLabelColors', async () => {
    const { writable } = await import('svelte/store');
    return { useCustomLabelColors: () => ({ customLabelColorsStore: writable({}) }) };
});
vi.mock('$lib/utils', () => ({ getColorByLabel: () => ({ color: '#00ff00' }) }));

function annotation(id: string, frameId = 'map'): AnnotationView {
    return {
        parent_sample_id: 'tick',
        sample_id: id,
        annotation_collection_id: 'source',
        annotation_type: 'cuboid_3d',
        annotation_label: { annotation_label_name: 'car' },
        created_at: new Date('2026-01-01'),
        cuboid_3d_details: {
            frame_id: frameId,
            px: 1,
            py: 2,
            pz: 3,
            qx: 0,
            qy: 0,
            qz: 0,
            qw: 1,
            sx: 4,
            sy: 5,
            sz: 6
        }
    };
}

function frame(frameId = 'map') {
    return {
        batch: { positions: new Float32Array(3), intensities: new Float32Array(1), count: 1 },
        channels: [{ frameId }],
        bounds: null
    };
}

let dispose = () => {};
afterEach(() => dispose());

function setup() {
    const workspace = $state({
        currentTick: 0,
        referenceFrameId: 'map',
        isShowingSensorFrames: false,
        cloudPointFrame: { data: frame(), isPlaceholderData: false },
        tickDetails: {
            data: {
                sample_id: 'tick-0',
                collection_id: 'source',
                tags: [],
                annotations: [annotation('map-box'), annotation('sensor-box', 'sensor')]
            },
            isPlaceholderData: false
        }
    });
    let data!: ReturnType<typeof useWorkspaceSceneData>;
    dispose = $effect.root(() => {
        data = useWorkspaceSceneData(
            () => workspace as unknown as PointCloudWorkspaceContext,
            () => ({ datasetId: 'dataset', sequenceId: 'sequence' })
        );
    });
    flushSync();
    return { workspace, data };
}

describe('scene snapshot consistency', () => {
    it.each(['cloud', 'annotations'] as const)(
        'retains the cloud but clears stale annotations until both queries finish (%s first)',
        (first) => {
            const { workspace, data } = setup();
            const initialCloud = data.snapshot?.frame;
            workspace.currentTick = 1;
            workspace.referenceFrameId = 'sensor';
            workspace.isShowingSensorFrames = true;
            workspace.cloudPointFrame.isPlaceholderData = true;
            workspace.tickDetails.isPlaceholderData = true;
            flushSync();

            expect(data.snapshot?.frame).toBe(initialCloud);
            expect(data.snapshotAnnotations).toEqual([]);
            expect(data.cuboids).toEqual([]);
            expect(data.tick?.isStale).toBe(true);
            expect(data.currentSnapshot).toBeUndefined();

            workspace.cloudPointFrame.data = frame('sensor');
            workspace.tickDetails.data = {
                ...workspace.tickDetails.data,
                sample_id: 'tick-1',
                annotations: [annotation('next-box', 'sensor')]
            };
            const firstQuery =
                first === 'cloud' ? workspace.cloudPointFrame : workspace.tickDetails;
            const lastQuery = first === 'cloud' ? workspace.tickDetails : workspace.cloudPointFrame;
            firstQuery.isPlaceholderData = false;
            flushSync();
            expect(data.snapshot?.fitKey).toBe('sequence/map/false');
            expect(data.cuboids).toEqual([]);

            lastQuery.isPlaceholderData = false;
            flushSync();
            expect(data.currentSnapshot?.tick).toBe(1);
            expect(data.snapshot?.fitKey).toBe('sequence/sensor/true');
            expect(data.snapshot?.frame).toBe(workspace.cloudPointFrame.data);
            expect(data.cuboids.map(({ id }) => id)).toEqual(['next-box']);
            expect(data.tick).toMatchObject({ sampleId: 'tick-1', isStale: false });
        }
    );

    it('only renders annotations in the loaded coordinate frame, including sensor fallback', () => {
        const { workspace, data } = setup();
        expect(data.cuboids.map(({ id }) => id)).toEqual(['map-box']);
        workspace.cloudPointFrame.data = frame('sensor');
        workspace.isShowingSensorFrames = true;
        flushSync();
        expect(data.cuboids.map(({ id }) => id)).toEqual(['sensor-box']);
    });
});
