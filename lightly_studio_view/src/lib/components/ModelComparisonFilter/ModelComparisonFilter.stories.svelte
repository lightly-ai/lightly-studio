<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';

    const { Story } = defineMeta({
        title: 'Prototypes/ModelComparisonFilter',
        tags: ['autodocs']
    });
</script>

<script lang="ts">
    import Grid from '$lib/components/Grid/Grid.svelte';
    import GridItem from '$lib/components/GridItem/GridItem.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { Label } from '$lib/components/ui/label/index.js';
    import { Slider } from '$lib/components/ui/slider';

    // ── Types ────────────────────────────────────────────────────────────────

    type ModelDef = { id: string; name: string; color: string; enabled: boolean };
    type LabelDef = { name: string; enabled: boolean };
    type BBox = {
        x: number;
        y: number;
        w: number;
        h: number;
        label: string;
        modelId: string;
        confidence: number;
    };
    type ImageData = { index: number; width: number; height: number; bboxes: BBox[] };

    // ── Fake data ────────────────────────────────────────────────────────────

    const ALL_LABELS = ['cat', 'dog', 'car', 'person', 'bicycle'];
    const MODEL_DEFS: ModelDef[] = [
        { id: 'ground_truth', name: 'ground_truth', color: '#22c55e', enabled: true },
        { id: 'yolo_v8', name: 'yolo_v8', color: '#3b82f6', enabled: true },
        { id: 'predictions_a', name: 'predictions_a', color: '#f97316', enabled: false }
    ];

    function seededRand(seed: number): number {
        const x = Math.sin(seed + 1) * 10000;
        return x - Math.floor(x);
    }

    function generateImage(imageIndex: number): ImageData {
        let seed = imageIndex * 97;
        const width = Math.round(seededRand(seed++) * 3800 + 200);
        const height = Math.round(seededRand(seed++) * 3800 + 200);
        const bboxes: BBox[] = [];

        for (const modelId of MODEL_DEFS.map((m) => m.id)) {
            const boxCount = Math.floor(seededRand(seed++) * 3) + 1;
            for (let b = 0; b < boxCount; b++) {
                bboxes.push({
                    x: seededRand(seed++) * 0.5,
                    y: seededRand(seed++) * 0.5,
                    w: seededRand(seed++) * 0.35 + 0.1,
                    h: seededRand(seed++) * 0.35 + 0.1,
                    label: ALL_LABELS[Math.floor(seededRand(seed++) * ALL_LABELS.length)],
                    confidence: Math.round(seededRand(seed++) * 100) / 100,
                    modelId
                });
            }
        }

        return { index: imageIndex, width, height, bboxes };
    }

    const TOTAL_IMAGES = 48;
    const ALL_IMAGES: ImageData[] = Array.from({ length: TOTAL_IMAGES }, (_, i) =>
        generateImage(i)
    );

    // ── Reactive state ───────────────────────────────────────────────────────

    let models: ModelDef[] = $state(MODEL_DEFS.map((m) => ({ ...m })));
    let labelDefs: LabelDef[] = $state(ALL_LABELS.map((name) => ({ name, enabled: true })));

    let widthRange = $state([0, 4000]);
    let heightRange = $state([0, 4000]);

    const enabledModelIds = $derived(new Set(models.filter((m) => m.enabled).map((m) => m.id)));
    const enabledLabels = $derived(new Set(labelDefs.filter((l) => l.enabled).map((l) => l.name)));
    const modelColorMap = $derived(Object.fromEntries(models.map((m) => [m.id, m.color])));

    const colorByLabel = $derived(enabledModelIds.size === 1);

    const LABEL_COLORS: Record<string, string> = {
        cat: '#f43f5e',
        dog: '#f97316',
        car: '#eab308',
        person: '#22c55e',
        bicycle: '#6366f1'
    };

    function bboxColor(modelId: string, label: string): string {
        return colorByLabel
            ? (LABEL_COLORS[label] ?? '#ffffff')
            : (modelColorMap[modelId] ?? '#ffffff');
    }

    function toggleModel(id: string) {
        models = models.map((m) => (m.id === id ? { ...m, enabled: !m.enabled } : m));
    }

    function toggleLabel(name: string) {
        labelDefs = labelDefs.map((l) => (l.name === name ? { ...l, enabled: !l.enabled } : l));
    }

    const visibleImages = $derived(
        ALL_IMAGES.filter((img) => {
            if (img.width < widthRange[0] || img.width > widthRange[1]) return false;
            if (img.height < heightRange[0] || img.height > heightRange[1]) return false;
            return img.bboxes.some(
                (b) =>
                    enabledModelIds.has(b.modelId) &&
                    enabledLabels.has(b.label)
            );
        })
    );

    const visibleCount = $derived(visibleImages.length);

    // Per-label: how many visible images have ≥1 annotation of that label from any enabled collection
    const labelImageCounts = $derived(
        Object.fromEntries(
            ALL_LABELS.map((lbl) => [
                lbl,
                visibleImages.filter((img) =>
                    img.bboxes.some((b) => enabledModelIds.has(b.modelId) && b.label === lbl)
                ).length
            ])
        )
    );

    // ── Helpers ──────────────────────────────────────────────────────────────

    function hexToRgba(hex: string, alpha: number): string {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }


    const DIM_MAX = 4000;
    const columnCount = 5;
</script>

<Story name="Comparison View" asChild>
    <div class="flex h-screen w-full overflow-hidden bg-background text-foreground">
        <!-- ── Sidebar ───────────────────────────────────────────────────── -->
        <aside
            class="w-90 flex shrink-0 flex-col gap-4 overflow-y-auto border-r border-border px-3 py-4"
        >
            <!-- Annotation Collections -->
            <Segment title="Annotation Collections">
                <div class="space-y-2">
                    {#each models as model (model.id)}
                        <div class="space-y-1" title={model.name}>
                            <div class="flex items-center space-x-2">
                                <Checkbox
                                    id={`model-${model.id}`}
                                    checked={model.enabled}
                                    aria-labelledby={`model-${model.id}-label`}
                                    onCheckedChange={() => toggleModel(model.id)}
                                />
                                <Label
                                    id={`model-${model.id}-label`}
                                    for={`model-${model.id}`}
                                    class="flex min-w-0 flex-1 cursor-pointer items-center space-x-2 text-nowrap"
                                >
                                    <span
                                        class="inline-block h-3 w-3 shrink-0 rounded-sm border"
                                        style="background-color: {hexToRgba(
                                            model.color,
                                            0.35
                                        )}; border-color: {model.color};"
                                    ></span>
                                    <span class="flex-1 truncate text-sm font-normal"
                                        >{model.name}</span
                                    >
                                </Label>
                            </div>
                        </div>
                    {/each}
                </div>
            </Segment>

            <!-- Labels -->
            <Segment title="Labels">
                <div class="space-y-2">
                    {#each labelDefs as lbl (lbl.name)}
                        <div class="flex items-center space-x-2" title={lbl.name}>
                            <Checkbox
                                id={`label-${lbl.name}`}
                                checked={lbl.enabled}
                                aria-labelledby={`label-${lbl.name}-label`}
                                onCheckedChange={() => toggleLabel(lbl.name)}
                            />
                            <Label
                                id={`label-${lbl.name}-label`}
                                for={`label-${lbl.name}`}
                                class="flex min-w-0 flex-1 cursor-pointer items-center space-x-2 text-nowrap"
                            >
                                {#if colorByLabel}
                                    <span
                                        class="inline-block h-3 w-3 shrink-0 rounded-sm border transition-colors"
                                        style="background-color: {hexToRgba(
                                            LABEL_COLORS[lbl.name] ?? '#ffffff',
                                            0.35
                                        )}; border-color: {LABEL_COLORS[lbl.name] ?? '#ffffff'};"
                                    ></span>
                                {/if}
                                <span class="flex-1 truncate text-sm font-normal">{lbl.name}</span>
                                {#if labelImageCounts[lbl.name]}
                                    <span class="shrink-0 text-xs text-muted-foreground tabular-nums">
                                        {labelImageCounts[lbl.name]}
                                    </span>
                                {/if}
                            </Label>
                        </div>
                    {/each}
                </div>
            </Segment>

            <!-- Dimensions filter -->
            <Segment title="Dimensions">
                <div class="space-y-3 text-xs">
                    <div class="space-y-2">
                        <div class="flex items-center justify-between text-muted-foreground">
                            <span>Width</span>
                            <span class="tabular-nums">{widthRange[0]} – {widthRange[1]} px</span>
                        </div>
                        <Slider min={0} max={DIM_MAX} step={100} bind:value={widthRange} />
                    </div>
                    <div class="space-y-2">
                        <div class="flex items-center justify-between text-muted-foreground">
                            <span>Height</span>
                            <span class="tabular-nums">{heightRange[0]} – {heightRange[1]} px</span>
                        </div>
                        <Slider min={0} max={DIM_MAX} step={100} bind:value={heightRange} />
                    </div>
                </div>
            </Segment>
        </aside>

        <!-- ── Main area ─────────────────────────────────────────────────── -->
        <div class="flex min-w-0 flex-1 flex-col">
            <!-- Header bar -->
            <div
                class="flex items-center gap-3 border-b border-border px-4 py-2 text-sm text-muted-foreground"
            >
                <span>{visibleCount} of {TOTAL_IMAGES} images</span>
            </div>

            <!-- Grid -->
            <div class="min-h-0 flex-1">
                {#if visibleCount === 0}
                    <div class="flex h-full items-center justify-center text-muted-foreground">
                        No images match the current filters.
                    </div>
                {:else}
                    <Grid itemCount={visibleCount} {columnCount}>
                        {#snippet gridItem({
                            index,
                            style,
                            width,
                            height
                        }: {
                            index: number;
                            style: string;
                            width: number;
                            height: number;
                        })}
                            {@const img = visibleImages[index]}
                            <GridItem {width} {height} {style} tag={false}>
                                <img
                                    src="https://picsum.photos/{Math.round(width)}/{Math.round(
                                        height
                                    )}?random={img.index}"
                                    alt="Sample {img.index + 1}"
                                    class="h-full w-full object-cover"
                                    loading="lazy"
                                />
                                <!-- Dimension badge -->
                                <span
                                    class="pointer-events-none absolute bottom-1 right-1 z-10 rounded bg-black/50 px-1 py-0.5 text-[9px] tabular-nums text-white"
                                >
                                    {img.width}×{img.height}
                                </span>

                                <!-- Bbox overlays -->
                                <div class="pointer-events-none absolute inset-0">
                                    {#each img.bboxes as bbox}
                                        {#if enabledModelIds.has(bbox.modelId) && enabledLabels.has(bbox.label)}
                                            {@const color = bboxColor(bbox.modelId, bbox.label)}
                                            <div
                                                class="absolute"
                                                style="
                                                    left: {bbox.x * 100}%;
                                                    top: {bbox.y * 100}%;
                                                    width: {bbox.w * 100}%;
                                                    height: {bbox.h * 100}%;
                                                    border: 2px solid {color};
                                                    box-shadow: inset 0 0 0 1px {hexToRgba(
                                                    color,
                                                    0.25
                                                )};
                                                "
                                            >
                                                <span
                                                    class="absolute left-0 top-0 translate-y-[-100%] px-1 py-0.5 text-[9px] font-semibold leading-tight text-white"
                                                    style="background-color: {color};"
                                                >
                                                    {bbox.label}
                                                    {bbox.confidence.toFixed(2)}
                                                </span>
                                            </div>
                                        {/if}
                                    {/each}
                                </div>
                            </GridItem>
                        {/snippet}
                    </Grid>
                {/if}
            </div>
        </div>

    </div>
</Story>
