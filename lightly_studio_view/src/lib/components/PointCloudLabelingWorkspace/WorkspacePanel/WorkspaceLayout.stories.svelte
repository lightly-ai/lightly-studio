<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { Pane, PaneGroup, PaneResizer, type PaneAPI } from 'paneforge';
    import Camera from '@lucide/svelte/icons/camera';
    import ChartGantt from '@lucide/svelte/icons/chart-gantt';
    import Tags from '@lucide/svelte/icons/tags';
    import Focus from '@lucide/svelte/icons/focus';
    import Grid2x2 from '@lucide/svelte/icons/grid-2x2';
    import PanelBottom from '@lucide/svelte/icons/panel-bottom';
    import PanelRight from '@lucide/svelte/icons/panel-right';
    import Settings2 from '@lucide/svelte/icons/settings-2';
    import { Button } from '$lib/components';
    import { cn } from '$lib/utils';
    import { WorkspaceLayoutToggles } from '../WorkspaceLayoutToggles';
    import WorkspacePanel from './WorkspacePanel.svelte';

    const { Story } = defineMeta({
        title: 'Components/PointCloudLabelingWorkspace/WorkspaceLayout (prototype)',
        parameters: { layout: 'fullscreen' }
    });

    /** Panels that resize through a paneforge pane. */
    type PanePanelId = 'orthographic' | 'camera' | 'details';
    /** Panels inside the timeline: shown or hidden, the timeline pane follows their height. */
    type TrackPanelId = 'objectTracks' | 'tagTracks';
    type PanelId = PanePanelId | TrackPanelId;

    const PANEL_IDS: readonly PanelId[] = [
        'orthographic',
        'camera',
        'details',
        'objectTracks',
        'tagTracks'
    ];
    const isTrackPanel = (id: PanelId): id is TrackPanelId =>
        id === 'objectTracks' || id === 'tagTracks';

    /** Default size in percent of each pane; double-clicking a resizer restores it. */
    const DEFAULT_SIZES = { orthographic: 25, camera: 28, details: 22, timeline: 26 };
    /** Timeline height without track panels: the header and the frame ruler. */
    const COMPACT_TIMELINE_PX = 32 + 24;

    const CAMERAS = [
        'CAM_FRONT_LEFT',
        'CAM_FRONT',
        'CAM_FRONT_RIGHT',
        'CAM_BACK_LEFT',
        'CAM_BACK',
        'CAM_BACK_RIGHT'
    ];
    const TRACKS = [
        { name: 'Car 3', start: 2, end: 72, color: 'bg-amber-400' },
        { name: 'Pedestrian 7', start: 18, end: 52, color: 'bg-sky-400' },
        { name: 'Truck 1', start: 40, end: 98, color: 'bg-fuchsia-400' }
    ];
    const TAGS = [
        {
            name: 'Tag: occluded',
            ranges: [
                [6, 14],
                [45, 60]
            ]
        },
        { name: 'Tag: night', ranges: [[0, 100]] }
    ];
    const DETAILS = [
        ['Car 3', '4.6 × 1.9 × 1.5 m'],
        ['Pedestrian 7', '0.7 × 0.6 × 1.8 m'],
        ['Truck 1', '8.2 × 2.5 × 3.1 m']
    ];
</script>

<script lang="ts">
    /** Where the orthographic views dock: beside the scene (stacked) or below it (in a row). */
    let orthographicDock = $state<'right' | 'bottom'>('right');
    const orthographicIsBeside = $derived(orthographicDock === 'right');
    const panes = $state<Partial<Record<PanePanelId | 'timeline', PaneAPI>>>({});
    let shown = $state<Record<PanelId, boolean>>({
        orthographic: true,
        camera: true,
        details: true,
        objectTracks: true,
        tagTracks: true
    });
    let savedLayout = $state<Record<PanelId, boolean> | null>(null);
    let workspaceHeight = $state(0);
    let timelineSizeWithTracks = DEFAULT_SIZES.timeline;

    const toggles = $derived([
        {
            id: 'orthographic',
            label: 'Orthographic views',
            icon: Grid2x2,
            isActive: shown.orthographic
        },
        { id: 'camera', label: 'Camera strip', icon: Camera, isActive: shown.camera },
        {
            id: 'objectTracks',
            label: 'Object tracks',
            icon: ChartGantt,
            isActive: shown.objectTracks
        },
        { id: 'tagTracks', label: 'Frame tag tracks', icon: Tags, isActive: shown.tagTracks },
        { id: 'details', label: 'Right side panel', icon: PanelRight, isActive: shown.details }
    ]);
    const focusToggle = $derived([
        { id: 'focus', label: 'Focus on 3D scene', icon: Focus, isActive: savedLayout !== null }
    ]);

    const hasTracks = () => shown.objectTracks || shown.tagTracks;

    /**
     * Compacts the timeline pane when the last track panel closes and restores its size when
     * the first track panel opens.
     */
    const fitTimeline = (hadTracks: boolean) => {
        const timeline = panes.timeline;
        const hasTracksNow = hasTracks();
        if (!timeline || !workspaceHeight || hadTracks === hasTracksNow) return;
        if (hasTracksNow) {
            timeline.resize(timelineSizeWithTracks);
            return;
        }
        if (timeline.getSize() > 0) timelineSizeWithTracks = timeline.getSize();
        timeline.resize((COMPACT_TIMELINE_PX / workspaceHeight) * 100);
    };
    const setShown = (id: PanelId, isShown: boolean) => {
        const hadTracks = hasTracks();
        shown[id] = isShown;
        if (isShown) savedLayout = null;
        if (isTrackPanel(id)) fitTimeline(hadTracks);
    };
    const setPanel = (id: PanelId, isShown: boolean) => {
        if (isTrackPanel(id)) {
            setShown(id, isShown);
            return;
        }
        const pane = panes[id];
        if (isShown) pane?.expand();
        else pane?.collapse();
    };
    const togglePanel = (id: string) => setPanel(id as PanelId, !shown[id as PanelId]);
    const hide = (id: PanelId) => () => setPanel(id, false);
    const resetSize = (id: keyof typeof DEFAULT_SIZES) => () =>
        panes[id]?.resize(DEFAULT_SIZES[id]);

    const toggleFocus = () => {
        const restored = savedLayout;
        if (restored) {
            savedLayout = null;
            for (const id of PANEL_IDS) if (restored[id]) setPanel(id, true);
            return;
        }
        const snapshot = { ...shown };
        for (const id of PANEL_IDS) setPanel(id, false);
        savedLayout = snapshot;
    };
    const toggleOrthographicDock = () => {
        orthographicDock = orthographicIsBeside ? 'bottom' : 'right';
    };
</script>

{#snippet settings()}
    <Button
        variant="outline"
        icon={Settings2}
        buttonProps={{ type: 'button', size: 'xs', class: 'h-7 gap-1 px-2 text-xs' }}
    >
        Settings
    </Button>
{/snippet}

{#snippet placeholder(label: string)}
    <div class="flex h-full min-h-12 items-center justify-center bg-muted/40 text-xs">
        {label}
    </div>
{/snippet}

{#snippet cameraTiles()}
    <div class="flex h-full gap-2 px-2 pb-2">
        {#each CAMERAS as camera (camera)}
            <div class="flex min-w-0 flex-1 items-end bg-muted/40 p-2 text-xs">
                <span class="truncate">{camera}</span>
            </div>
        {/each}
    </div>
{/snippet}

{#snippet trackRows()}
    <div class="flex flex-col gap-1.5 px-3 py-2 text-xs">
        {#each TRACKS as track (track.name)}
            <div class="flex items-center gap-4">
                <span class="w-24 shrink-0 truncate">{track.name}</span>
                <div class="relative h-3 flex-1 rounded-sm bg-muted/40">
                    <div
                        class={cn('absolute inset-y-0 rounded-sm', track.color)}
                        style:left="{track.start}%"
                        style:width="{track.end - track.start}%"
                    ></div>
                </div>
            </div>
        {/each}
    </div>
{/snippet}

{#snippet tagRows()}
    <div class="flex flex-col gap-1.5 px-3 py-2 text-xs">
        {#each TAGS as tag (tag.name)}
            <div class="flex items-center gap-4">
                <span class="w-24 shrink-0 truncate">{tag.name}</span>
                <div class="relative h-3 flex-1 rounded-sm bg-muted/40">
                    {#each tag.ranges as [start, end] (start)}
                        <div
                            class="absolute inset-y-0 rounded-sm bg-muted-foreground/50"
                            style:left="{start}%"
                            style:width="{end - start}%"
                        ></div>
                    {/each}
                </div>
            </div>
        {/each}
    </div>
{/snippet}

{#snippet detailRows()}
    <dl class="flex flex-col gap-1 px-3 py-2 text-xs">
        {#each DETAILS as [name, size] (name)}
            <div class="flex justify-between">
                <dt>{name}</dt>
                <dd>{size}</dd>
            </div>
        {/each}
    </dl>
{/snippet}

{#snippet resizer(direction: 'horizontal' | 'vertical', isShown: boolean, onReset: () => void)}
    <PaneResizer
        class={cn(
            'bg-border transition-colors hover:bg-primary/60 data-[active=pointer]:bg-primary',
            direction === 'horizontal' ? 'w-1 cursor-col-resize' : 'h-1 cursor-row-resize',
            !isShown && 'hidden'
        )}
        ondblclick={onReset}
    />
{/snippet}

<Story name="Workspace layout">
    <div class="flex h-[46rem] flex-col overflow-hidden bg-background">
        <header class="flex h-11 shrink-0 items-center justify-between border-b px-3">
            <span class="text-sm text-muted-foreground">Dataset / Sequence 0042</span>
            <div class="flex items-center gap-2">
                <WorkspaceLayoutToggles {toggles} onToggle={togglePanel} />
                <div class="h-5 w-px bg-border"></div>
                <WorkspaceLayoutToggles toggles={focusToggle} onToggle={toggleFocus} />
            </div>
        </header>
        <div class="min-h-0 flex-1" bind:clientHeight={workspaceHeight}>
            <PaneGroup direction="vertical">
                <Pane defaultSize={100 - DEFAULT_SIZES.timeline} minSize={30}>
                    <PaneGroup direction="horizontal">
                        <Pane defaultSize={100 - DEFAULT_SIZES.details} minSize={40}>
                            <PaneGroup direction="vertical">
                                <Pane defaultSize={100 - DEFAULT_SIZES.camera} minSize={30}>
                                    <PaneGroup
                                        direction={orthographicIsBeside ? 'horizontal' : 'vertical'}
                                    >
                                        <Pane
                                            defaultSize={100 - DEFAULT_SIZES.orthographic}
                                            minSize={40}
                                        >
                                            <WorkspacePanel
                                                title="3D scene"
                                                actions={settings}
                                                class="h-full"
                                            >
                                                {@render placeholder('3D perspective view')}
                                            </WorkspacePanel>
                                        </Pane>
                                        {@render resizer(
                                            orthographicIsBeside ? 'horizontal' : 'vertical',
                                            shown.orthographic,
                                            resetSize('orthographic')
                                        )}
                                        <Pane
                                            bind:this={panes.orthographic}
                                            defaultSize={DEFAULT_SIZES.orthographic}
                                            minSize={12}
                                            maxSize={45}
                                            collapsible
                                            collapsedSize={0}
                                            onCollapse={() => setShown('orthographic', false)}
                                            onExpand={() => setShown('orthographic', true)}
                                        >
                                            {#if shown.orthographic}
                                                <WorkspacePanel
                                                    title="Orthographic views"
                                                    onHide={hide('orthographic')}
                                                    class="h-full"
                                                >
                                                    {#snippet actions()}
                                                        <Button
                                                            variant="ghost"
                                                            icon={orthographicIsBeside
                                                                ? PanelBottom
                                                                : PanelRight}
                                                            ariaLabel={orthographicIsBeside
                                                                ? 'Show views below the scene'
                                                                : 'Show views beside the scene'}
                                                            buttonProps={{
                                                                type: 'button',
                                                                size: 'xs',
                                                                class: 'h-7 w-7 p-0',
                                                                title: orthographicIsBeside
                                                                    ? 'Show views below the scene'
                                                                    : 'Show views beside the scene',
                                                                onclick: toggleOrthographicDock
                                                            }}
                                                        />
                                                    {/snippet}
                                                    <div
                                                        class={cn(
                                                            'flex h-full gap-1',
                                                            orthographicIsBeside
                                                                ? 'flex-col'
                                                                : 'flex-row'
                                                        )}
                                                    >
                                                        {#each ['Top', 'Side', 'Front'] as view (view)}
                                                            <div class="min-h-0 min-w-0 flex-1">
                                                                {@render placeholder(view)}
                                                            </div>
                                                        {/each}
                                                    </div>
                                                </WorkspacePanel>
                                            {/if}
                                        </Pane>
                                    </PaneGroup>
                                </Pane>
                                {@render resizer('vertical', shown.camera, resetSize('camera'))}
                                <Pane
                                    bind:this={panes.camera}
                                    defaultSize={DEFAULT_SIZES.camera}
                                    minSize={12}
                                    maxSize={50}
                                    collapsible
                                    collapsedSize={0}
                                    onCollapse={() => setShown('camera', false)}
                                    onExpand={() => setShown('camera', true)}
                                >
                                    {#if shown.camera}
                                        <WorkspacePanel
                                            title="Camera strip"
                                            onHide={hide('camera')}
                                            actions={settings}
                                            class="h-full"
                                        >
                                            {@render cameraTiles()}
                                        </WorkspacePanel>
                                    {/if}
                                </Pane>
                            </PaneGroup>
                        </Pane>
                        {@render resizer('horizontal', shown.details, resetSize('details'))}
                        <Pane
                            bind:this={panes.details}
                            defaultSize={DEFAULT_SIZES.details}
                            minSize={14}
                            maxSize={40}
                            collapsible
                            collapsedSize={0}
                            onCollapse={() => setShown('details', false)}
                            onExpand={() => setShown('details', true)}
                        >
                            {#if shown.details}
                                <WorkspacePanel
                                    title="Right side panel"
                                    onHide={hide('details')}
                                    class="h-full"
                                >
                                    <div class="flex flex-col gap-px bg-border">
                                        <WorkspacePanel title="Sequence tags">
                                            {@render placeholder('+ Add tag')}
                                        </WorkspacePanel>
                                        <WorkspacePanel title="Frame tags">
                                            {@render placeholder('+ Add tag')}
                                        </WorkspacePanel>
                                        <WorkspacePanel title="Annotations">
                                            {@render detailRows()}
                                        </WorkspacePanel>
                                    </div>
                                </WorkspacePanel>
                            {/if}
                        </Pane>
                    </PaneGroup>
                </Pane>
                {@render resizer(
                    'vertical',
                    shown.objectTracks || shown.tagTracks,
                    resetSize('timeline')
                )}
                <Pane
                    bind:this={panes.timeline}
                    defaultSize={DEFAULT_SIZES.timeline}
                    minSize={5}
                    maxSize={50}
                >
                    <WorkspacePanel title="Timeline" class="h-full">
                        {#snippet actions()}
                            <span class="text-muted-foreground">⏮ ▶ ⏭ · Frame 12 / 240</span>
                        {/snippet}
                        <div class="flex h-full flex-col overflow-y-auto">
                            <div class="h-6 shrink-0 bg-muted/60 text-center text-xs">
                                Frame ruler
                            </div>
                            {#if shown.objectTracks}
                                <WorkspacePanel
                                    title="Object tracks"
                                    onHide={hide('objectTracks')}
                                    class="shrink-0"
                                >
                                    {#snippet actions()}
                                        <Button
                                            variant="outline"
                                            buttonProps={{
                                                type: 'button',
                                                size: 'xs',
                                                class: 'h-6 text-xs'
                                            }}
                                        >
                                            Add object track
                                        </Button>
                                    {/snippet}
                                    {@render trackRows()}
                                </WorkspacePanel>
                            {/if}
                            {#if shown.tagTracks}
                                <WorkspacePanel
                                    title="Frame tag tracks"
                                    onHide={hide('tagTracks')}
                                    class="shrink-0"
                                >
                                    {@render tagRows()}
                                </WorkspacePanel>
                            {/if}
                        </div>
                    </WorkspacePanel>
                </Pane>
            </PaneGroup>
        </div>
    </div>
</Story>
