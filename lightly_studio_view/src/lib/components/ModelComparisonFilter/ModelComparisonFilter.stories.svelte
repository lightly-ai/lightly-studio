<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';

    const { Story } = defineMeta({
        title: 'Prototypes/ModelComparisonFilter',
        tags: ['autodocs'],
        argTypes: {
            imageCount: {
                control: { type: 'select' },
                options: [12, 24, 48, 100],
                description: 'Number of images in the grid'
            }
        }
    });
</script>

<script lang="ts">
    import Grid from '$lib/components/Grid/Grid.svelte';
    import GridItem from '$lib/components/GridItem/GridItem.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { Label } from '$lib/components/ui/label/index.js';

    // ── Types ────────────────────────────────────────────────────────────────

    type ModelDef = {
        id: string;
        name: string;
        color: string;
        enabled: boolean;
    };

    type LabelDef = {
        name: string;
        enabled: boolean;
    };

    type BBox = {
        /** Normalised 0–1 coordinates relative to image size */
        x: number;
        y: number;
        w: number;
        h: number;
        label: string;
        modelId: string;
    };

    // ── Fake data generation ─────────────────────────────────────────────────

    const ALL_LABELS = ['cat', 'dog', 'car', 'person', 'bicycle'];

    const MODEL_DEFS: ModelDef[] = [
        { id: 'ground_truth', name: 'ground_truth', color: '#22c55e', enabled: true },
        { id: 'yolo_v8', name: 'yolo_v8', color: '#3b82f6', enabled: true },
        { id: 'predictions_a', name: 'predictions_a', color: '#f97316', enabled: false }
    ];

    /** Seeded-ish pseudo-random so images look consistent on re-render */
    function seededRand(seed: number): number {
        const x = Math.sin(seed + 1) * 10000;
        return x - Math.floor(x);
    }

    function generateBBoxes(imageIndex: number): BBox[] {
        const boxes: BBox[] = [];
        const modelIds = ['ground_truth', 'yolo_v8', 'predictions_a'];
        let seed = imageIndex * 97;

        for (const modelId of modelIds) {
            const boxCount = Math.floor(seededRand(seed++) * 3) + 1;
            for (let b = 0; b < boxCount; b++) {
                const x = seededRand(seed++) * 0.5;
                const y = seededRand(seed++) * 0.5;
                const w = seededRand(seed++) * 0.35 + 0.1;
                const h = seededRand(seed++) * 0.35 + 0.1;
                const labelIdx = Math.floor(seededRand(seed++) * ALL_LABELS.length);
                boxes.push({ x, y, w, h, label: ALL_LABELS[labelIdx], modelId });
            }
        }
        return boxes;
    }

    // ── Reactive state ───────────────────────────────────────────────────────

    let imageCount = $state(24);
    const columnCount = 5;

    let models: ModelDef[] = $state(MODEL_DEFS.map((m) => ({ ...m })));
    let labelDefs: LabelDef[] = $state(ALL_LABELS.map((name) => ({ name, enabled: true })));

    const enabledModelIds = $derived(new Set(models.filter((m) => m.enabled).map((m) => m.id)));
    const enabledLabels = $derived(new Set(labelDefs.filter((l) => l.enabled).map((l) => l.name)));

    const modelColorMap = $derived(Object.fromEntries(models.map((m) => [m.id, m.color])));

    function toggleModel(id: string) {
        models = models.map((m) => (m.id === id ? { ...m, enabled: !m.enabled } : m));
    }

    function toggleLabel(name: string) {
        labelDefs = labelDefs.map((l) => (l.name === name ? { ...l, enabled: !l.enabled } : l));
    }

    /** Derive visible images: only include images that have at least one visible annotation */
    const allImages = $derived(
        Array.from({ length: imageCount }, (_, i) => ({
            index: i,
            bboxes: generateBBoxes(i)
        }))
    );

    const visibleImages = $derived(
        allImages.filter((img) =>
            img.bboxes.some((b) => enabledModelIds.has(b.modelId) && enabledLabels.has(b.label))
        )
    );

    const visibleCount = $derived(visibleImages.length);

    // ── Helpers ──────────────────────────────────────────────────────────────

    /** Returns hex with opacity as rgba string for CSS border */
    function hexToRgba(hex: string, alpha: number): string {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
</script>

<Story name="Comparison View" asChild>
    <div class="flex h-screen w-full overflow-hidden bg-background text-foreground">
        <!-- ── Sidebar ───────────────────────────────────────────────────── -->
        <aside
            class="flex w-60 shrink-0 flex-col gap-4 overflow-y-auto border-r border-border px-3 py-4"
        >
            <hr class="border-border" />

            <!-- Models -->
            <Segment title="Models">
                <div class="space-y-2">
                    {#each models as model (model.id)}
                        <div class="flex items-center space-x-2" title={model.name}>
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
                                <!-- Color swatch -->
                                <span
                                    class="inline-block h-3 w-3 shrink-0 rounded-sm border"
                                    style="background-color: {hexToRgba(
                                        model.color,
                                        0.35
                                    )}; border-color: {model.color};"
                                ></span>
                                <span class="flex-1 truncate text-sm font-normal">{model.name}</span
                                >
                            </Label>
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
                                class="flex min-w-0 flex-1 cursor-pointer items-center text-nowrap"
                            >
                                <span class="flex-1 truncate text-sm font-normal">{lbl.name}</span>
                            </Label>
                        </div>
                    {/each}
                </div>
            </Segment>
        </aside>

        <!-- ── Main grid area ────────────────────────────────────────────── -->
        <div class="flex min-w-0 flex-1 flex-col">
            <!-- Header bar -->
            <div
                class="flex items-center gap-3 border-b border-border px-4 py-2 text-sm text-muted-foreground"
            >
                <span>{visibleCount} of {imageCount} images</span>
                <!-- Model legend pills -->
                <div class="ml-auto flex gap-2">
                    {#each models.filter((m) => m.enabled) as model (model.id)}
                        <span
                            class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium"
                            style="background-color: {hexToRgba(
                                model.color,
                                0.15
                            )}; color: {model.color}; border: 1px solid {hexToRgba(
                                model.color,
                                0.4
                            )};"
                        >
                            <span
                                class="inline-block h-2 w-2 rounded-full"
                                style="background-color: {model.color};"
                            ></span>
                            {model.name}
                        </span>
                    {/each}
                </div>
            </div>

            <!-- Grid -->
            <div class="min-h-0 flex-1">
                {#if visibleCount === 0}
                    <div class="flex h-full items-center justify-center text-muted-foreground">
                        No images match the current filters.
                    </div>
                {:else}
                    <Grid itemCount={visibleCount} {columnCount}>
                        {#snippet gridItem({ index, style, width, height })}
                            {@const img = visibleImages[index]}
                            <GridItem {width} {height} {style} tag={false}>
                                <!-- Image thumbnail via picsum (seeded by original index) -->
                                <img
                                    src="https://picsum.photos/{Math.round(width)}/{Math.round(
                                        height
                                    )}?random={img.index}"
                                    alt="Sample {img.index + 1}"
                                    class="h-full w-full object-cover"
                                    loading="lazy"
                                />

                                <!-- Annotation bbox overlays (CSS, no canvas worker needed) -->
                                <div class="pointer-events-none absolute inset-0">
                                    {#each img.bboxes as bbox}
                                        {#if enabledModelIds.has(bbox.modelId) && enabledLabels.has(bbox.label)}
                                            {@const color =
                                                modelColorMap[bbox.modelId] ?? '#ffffff'}
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
                                                <!-- Label chip -->
                                                <span
                                                    class="absolute left-0 top-0 translate-y-[-100%] px-1 py-0.5 text-[9px] font-semibold leading-tight text-white"
                                                    style="background-color: {color};"
                                                >
                                                    {bbox.label}
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
