<script lang="ts">
    import maplibregl, {
        type GeoJSONSource,
        type LngLatBoundsLike,
        type StyleSpecification
    } from 'maplibre-gl';
    import type { FeatureCollection } from 'geojson';
    import 'maplibre-gl/dist/maplibre-gl.css';
    import Button from '$lib/components/ui/button/button.svelte';
    import { cn } from '$lib/utils/shadcn';
    import { getColorByLabel } from '$lib/utils';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import {
        useGpsCoordinates,
        type GpsCoordinatesFilter
    } from '$lib/hooks/useGpsCoordinates/useGpsCoordinates';
    import { page } from '$app/state';
    import { isVideosRoute } from '$lib/routes';
    import {
        bboxFromCorners,
        colorForPoint,
        sampleIdsInBbox,
        type GpsPoint,
        type GpsTag
    } from './gpsMapUtils';
    import { UNASSIGNED_COLOR } from '$lib/components/PlotPanel/plotColorUtils';

    let { collectionId, gpsKey }: { collectionId: string; gpsKey: string } = $props();

    const { setActivePanel } = useGlobalStorage();
    function handleClose() {
        setActivePanel('none');
    }

    // GPS lives on samples; wire the image/video shared filter like the embedding plot.
    const isVideos = $derived(isVideosRoute(page.route?.id ?? null));
    const imageFilters = useImageFilters();
    const videoFilters = useVideoFilters();
    const updateSampleIds = $derived(
        isVideos ? videoFilters.updateSampleIds : imageFilters.updateSampleIds
    );
    const imageFilter = $derived(isVideos ? null : imageFilters.imageFilter);
    const videoFilter = $derived(isVideos ? videoFilters.videoFilter : null);

    // Send the active filter with sample_ids stripped, so a prior rectangle
    // selection doesn't collapse the map — the full geographic spread stays visible.
    const filter = $derived.by((): GpsCoordinatesFilter => {
        const current = isVideos ? $videoFilter : $imageFilter;
        if (!current) return null;
        if (!current.sample_filter) return current as GpsCoordinatesFilter;
        return {
            ...current,
            sample_filter: { ...current.sample_filter, sample_ids: [] }
        } as GpsCoordinatesFilter;
    });

    const gpsQuery = $derived(useGpsCoordinates(() => ({ collectionId, key: gpsKey, filter })));
    const points = $derived<GpsPoint[]>(
        (gpsQuery.data ?? []).map((point) => ({
            sampleId: point.sample_id,
            lat: point.lat,
            lon: point.lon,
            tagIds: point.tag_ids ?? []
        }))
    );

    // Sample tags available to color/compare by.
    const { tags } = useTags({ collection_id: collectionId, kind: ['sample'] });
    // Ordered selection: index 0 has the highest coloring priority.
    let selectedTagIds = $state<string[]>([]);
    const selectedTags = $derived<GpsTag[]>(
        selectedTagIds
            .map((tagId) => $tags.find((tag) => tag.tag_id === tagId))
            .filter((tag): tag is NonNullable<typeof tag> => tag !== undefined)
            .map((tag) => ({ tagId: tag.tag_id, name: tag.name }))
    );

    function toggleTag(tagId: string) {
        selectedTagIds = selectedTagIds.includes(tagId)
            ? selectedTagIds.filter((id) => id !== tagId)
            : [...selectedTagIds, tagId];
    }

    const SOURCE_ID = 'gps-points';
    const LAYER_ID = 'gps-points-circles';

    // OpenStreetMap raster basemap — no API key required.
    const mapStyle: StyleSpecification = {
        version: 8,
        sources: {
            osm: {
                type: 'raster',
                tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
                tileSize: 256,
                attribution: '© OpenStreetMap contributors'
            }
        },
        layers: [{ id: 'osm', type: 'raster', source: 'osm' }]
    };

    let mapContainer: HTMLDivElement | null = $state(null);
    let map: maplibregl.Map | null = null;
    let mapLoaded = $state(false);
    let hasFitBounds = false;

    function buildFeatureCollection(): FeatureCollection {
        return {
            type: 'FeatureCollection',
            features: points.map((point) => ({
                type: 'Feature',
                geometry: { type: 'Point', coordinates: [point.lon, point.lat] },
                properties: {
                    sample_id: point.sampleId,
                    color: colorForPoint(point.tagIds, selectedTags)
                }
            }))
        };
    }

    function refreshSource() {
        if (!map || !mapLoaded) return;
        const source = map.getSource(SOURCE_ID) as GeoJSONSource | undefined;
        if (source) source.setData(buildFeatureCollection());
    }

    function fitToPoints() {
        if (!map || points.length === 0 || hasFitBounds) return;
        let west = Infinity;
        let south = Infinity;
        let east = -Infinity;
        let north = -Infinity;
        for (const point of points) {
            west = Math.min(west, point.lon);
            east = Math.max(east, point.lon);
            south = Math.min(south, point.lat);
            north = Math.max(north, point.lat);
        }
        const bounds: LngLatBoundsLike = [
            [west, south],
            [east, north]
        ];
        map.fitBounds(bounds, { padding: 40, maxZoom: 12, duration: 0 });
        hasFitBounds = true;
    }

    // ---- Shift+drag rectangle selection -------------------------------------
    let selectionBox = $state<{ x: number; y: number; width: number; height: number } | null>(null);
    let dragStart: { x: number; y: number } | null = null;

    function onCanvasMouseDown(event: MouseEvent) {
        if (!event.shiftKey || !map) return;
        event.preventDefault();
        map.dragPan.disable();
        const rect = map.getCanvasContainer().getBoundingClientRect();
        dragStart = { x: event.clientX - rect.left, y: event.clientY - rect.top };
        selectionBox = { x: dragStart.x, y: dragStart.y, width: 0, height: 0 };
    }

    function onCanvasMouseMove(event: MouseEvent) {
        if (!dragStart || !map) return;
        const rect = map.getCanvasContainer().getBoundingClientRect();
        const current = { x: event.clientX - rect.left, y: event.clientY - rect.top };
        selectionBox = {
            x: Math.min(dragStart.x, current.x),
            y: Math.min(dragStart.y, current.y),
            width: Math.abs(current.x - dragStart.x),
            height: Math.abs(current.y - dragStart.y)
        };
    }

    function onCanvasMouseUp(event: MouseEvent) {
        if (!dragStart || !map) return;
        const rect = map.getCanvasContainer().getBoundingClientRect();
        const end = { x: event.clientX - rect.left, y: event.clientY - rect.top };
        const dragged = Math.abs(end.x - dragStart.x) > 2 && Math.abs(end.y - dragStart.y) > 2;

        if (dragged) {
            const cornerA = map.unproject([dragStart.x, dragStart.y]);
            const cornerB = map.unproject([end.x, end.y]);
            const bbox = bboxFromCorners(
                { lat: cornerA.lat, lon: cornerA.lng },
                { lat: cornerB.lat, lon: cornerB.lng }
            );
            updateSampleIds(sampleIdsInBbox(points, bbox));
        }

        dragStart = null;
        selectionBox = null;
        map.dragPan.enable();
    }

    function clearSelection() {
        updateSampleIds([]);
    }

    $effect(() => {
        if (!mapContainer) return;

        const instance = new maplibregl.Map({
            container: mapContainer,
            style: mapStyle,
            center: [8.4, 47.3],
            zoom: 8,
            attributionControl: { compact: true }
        });
        instance.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
        // We use shift+drag for rectangle selection, so disable the built-in box zoom.
        instance.boxZoom.disable();

        instance.on('load', () => {
            instance.addSource(SOURCE_ID, {
                type: 'geojson',
                data: { type: 'FeatureCollection', features: [] }
            });
            instance.addLayer({
                id: LAYER_ID,
                type: 'circle',
                source: SOURCE_ID,
                paint: {
                    'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 2, 12, 5],
                    'circle-color': ['get', 'color'],
                    'circle-opacity': 0.85,
                    'circle-stroke-width': 0.5,
                    'circle-stroke-color': '#00000055'
                }
            });
            mapLoaded = true;
            refreshSource();
            fitToPoints();
        });

        const canvasContainer = instance.getCanvasContainer();
        canvasContainer.addEventListener('mousedown', onCanvasMouseDown);
        window.addEventListener('mousemove', onCanvasMouseMove);
        window.addEventListener('mouseup', onCanvasMouseUp);

        map = instance;

        return () => {
            canvasContainer.removeEventListener('mousedown', onCanvasMouseDown);
            window.removeEventListener('mousemove', onCanvasMouseMove);
            window.removeEventListener('mouseup', onCanvasMouseUp);
            instance.remove();
            map = null;
            mapLoaded = false;
            hasFitBounds = false;
        };
    });

    // Recolor / refill whenever the points or the selected tags change.
    $effect(() => {
        void points;
        void selectedTags;
        refreshSource();
        fitToPoints();
    });
</script>

<div class="flex min-h-0 flex-1 flex-col rounded-[1vw] bg-card p-4" data-testid="gps-map-panel">
    <div class="mb-3 mt-2 flex items-center justify-between">
        <div class="text-lg font-semibold">GPS Map</div>
        <Button
            variant="ghost"
            size="icon"
            onclick={handleClose}
            class="h-8 w-8"
            data-testid="gps-map-close-button"
        >
            ✕
        </Button>
    </div>

    {#if $tags.length > 0}
        <div class="mb-3 flex flex-wrap items-center gap-1.5" data-testid="gps-map-tag-picker">
            <span class="mr-1 text-xs text-muted-foreground">Color by tag:</span>
            {#each $tags as tag (tag.tag_id)}
                {@const selected = selectedTagIds.includes(tag.tag_id)}
                <button
                    class={cn(
                        'flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs transition-colors',
                        selected
                            ? 'border-transparent text-white'
                            : 'border-border text-muted-foreground hover:bg-accent'
                    )}
                    style={selected ? `background-color: ${getColorByLabel(tag.name).color}` : ''}
                    onclick={() => toggleTag(tag.tag_id)}
                >
                    <span
                        class="inline-block size-2 rounded-full"
                        style={`background-color: ${getColorByLabel(tag.name).color}`}
                    ></span>
                    {tag.name}
                </button>
            {/each}
        </div>
    {/if}

    <div class="relative min-h-0 flex-1 overflow-hidden rounded-md">
        <div bind:this={mapContainer} class="h-full w-full"></div>
        {#if selectionBox}
            <div
                class="pointer-events-none absolute border-2 border-primary bg-primary/20"
                style={`left:${selectionBox.x}px;top:${selectionBox.y}px;width:${selectionBox.width}px;height:${selectionBox.height}px`}
            ></div>
        {/if}
        {#if gpsQuery.isLoading}
            <div
                class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded bg-card/90 px-3 py-1.5 text-sm"
            >
                Loading GPS points…
            </div>
        {/if}
    </div>

    <div class="mt-2 flex shrink-0 flex-wrap items-center justify-between gap-2 text-xs">
        <div class="flex flex-wrap items-center gap-3 text-muted-foreground">
            {#if selectedTags.length > 0}
                {#each selectedTags as tag (tag.tagId)}
                    <span class="flex items-center gap-1">
                        <span
                            class="inline-block size-2 rounded-full"
                            style={`background-color: ${getColorByLabel(tag.name).color}`}
                        ></span>
                        {tag.name}
                    </span>
                {/each}
                <span class="flex items-center gap-1">
                    <span
                        class="inline-block size-2 rounded-full"
                        style={`background-color: ${UNASSIGNED_COLOR}`}
                    ></span>
                    none
                </span>
            {:else}
                <span>Shift + drag to select an area. {points.length.toLocaleString()} points.</span
                >
            {/if}
        </div>
        <Button variant="outline" size="sm" class="px-2.5" onclick={clearSelection}>
            Clear selection
        </Button>
    </div>
</div>
