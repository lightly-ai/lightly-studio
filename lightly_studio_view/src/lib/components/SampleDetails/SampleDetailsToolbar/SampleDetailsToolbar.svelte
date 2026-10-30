<script lang="ts">
    import { AnnotationType } from '$lib/api/lightly_studio_local';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import {
        isAssistedLabelingStatus,
        useSampleDetailsToolbarContext
    } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { onMount } from 'svelte';
    import { isOverlayTarget } from '$lib/utils';
    import { useSettings } from '$lib/hooks/useSettings';
    import { Toolbar, type ToolbarItem, type ToolbarTrigger } from '$lib/components/ui/toolbar';
    import { MousePointer, Hand, Brush, Bot, Layers3, WandSparkles } from '@lucide/svelte';
    import { VectorSquareIcon } from '$lib/components/VectorSquareIcon';
    import { useAssistedLabelingStatus } from '$lib/hooks/useAssistedLabelingStatus';
    import { isFrameDetailsRoute } from '$lib/routes';
    import { page } from '$app/state';

    import { getSlicEngine } from '@lightly-ai/slic';

    let slicAvailable = $state(false);
    onMount(() => {
        let active = true;
        void getSlicEngine().then(
            () => {
                if (active) slicAvailable = true;
            },
            // Unsupported or blocked WASM keeps the toolbar entry hidden.
            (error) => console.error('AI-assisted labeling initialization failed', error)
        );
        return () => {
            active = false;
        };
    });

    const {
        showSegmentationTool = true,
        isPending = false
    }: {
        showSegmentationTool?: boolean;
        isPending?: boolean;
    } = $props();

    const { settingsStore } = useSettings();

    let isSpacePressed = false;

    const {
        context: annotationLabelContext,
        setAnnotationId,
        setAnnotationType,
        setLastCreatedAnnotationId,
        setIsDrawing,
        setIsErasing
    } = useAnnotationLabelContext();

    const {
        context: sampleDetailsToolbarContext,
        setBrushMode,
        setStatus
    } = useSampleDetailsToolbarContext();

    const assistedLabelingStatus = useAssistedLabelingStatus();
    // Assisted labeling supports images only, not video frames.
    const showAssistedLabelingTools = $derived(
        !annotationLabelContext.isOnAnnotationDetailsView &&
            !isFrameDetailsRoute(page.route.id) &&
            assistedLabelingStatus.disabledReason === null
    );

    const items = $derived<ToolbarItem[]>([
        {
            id: 'cursor',
            label: 'Selection',
            icon: MousePointer,
            shortcut: $settingsStore.key_toolbar_selection,
            action: 'select'
        },
        {
            id: 'drag',
            label: 'Drag',
            icon: Hand,
            shortcut: $settingsStore.key_toolbar_drag,
            action: 'pan',
            hint: 'Hold Space to pan temporarily'
        },
        {
            id: 'bounding-box',
            label: 'Bounding Box Tool',
            icon: VectorSquareIcon,
            shortcut: $settingsStore.key_toolbar_bounding_box,
            action: 'draw',
            visible: !annotationLabelContext.isOnAnnotationDetailsView
        },
        {
            id: 'slic',
            label: 'AI-Assisted labeling',
            icon: Bot,
            shortcut: $settingsStore.key_toolbar_slic ?? 'a',
            action: 'activate',
            visible: showSegmentationTool && slicAvailable
        },
        {
            id: 'smart-select',
            label: 'Smart select',
            icon: WandSparkles,
            hint: 'Segments the object that you click or box. Sends the image to fal.ai.',
            visible: showAssistedLabelingTools
        },
        {
            id: 'find-instances',
            label: 'Find all instances',
            icon: Layers3,
            hint: 'Finds all objects that match a text prompt. Sends the image to fal.ai.',
            visible: showAssistedLabelingTools
        },
        {
            id: 'brush',
            label: 'Segmentation Mask Brush',
            icon: Brush,
            shortcut: $settingsStore.key_toolbar_segmentation_mask,
            action: 'paint',
            visible: showSegmentationTool
        }
    ]);

    function shouldHandleShortcut(e: KeyboardEvent): boolean {
        if (isOverlayTarget(e.target)) return false;

        if (e.code === 'Space') {
            isSpacePressed = true;
            return false;
        }

        if (isSpacePressed) return false;

        return true;
    }

    // Reset space tracking on keyup and window blur.
    onMount(() => {
        const onKeyUp = (e: KeyboardEvent) => {
            if (e.code === 'Space') isSpacePressed = false;
        };
        const onWindowBlur = () => {
            isSpacePressed = false;
        };
        window.addEventListener('keyup', onKeyUp);
        window.addEventListener('blur', onWindowBlur);
        return () => {
            window.removeEventListener('keyup', onKeyUp);
            window.removeEventListener('blur', onWindowBlur);
        };
    });

    const resetDrawing = () => {
        setAnnotationType(null);
        setLastCreatedAnnotationId(null);
        setIsDrawing(false);
        setIsErasing(false);
    };

    const applyDrawingTool = (status: 'bounding-box' | 'brush' | 'slic') => {
        setLastCreatedAnnotationId(null);
        if (status === 'brush') {
            setAnnotationType(AnnotationType.SEGMENTATION_MASK);
            return;
        }
        setBrushMode('brush');
        if (status === 'slic') {
            setAnnotationType(AnnotationType.SEGMENTATION_MASK);
        } else if (!annotationLabelContext.isOnAnnotationDetailsView) {
            setAnnotationType(AnnotationType.OBJECT_DETECTION);
        }
    };

    $effect(() => {
        const { status } = sampleDetailsToolbarContext;
        // Reset annotation label and type when switching to cursor tool
        if (status === 'cursor') {
            if (!annotationLabelContext.isOnAnnotationDetailsView) setAnnotationId(null);
            resetDrawing();
            setBrushMode('brush');
        } else if (status === 'bounding-box' || status === 'brush' || status === 'slic') {
            applyDrawingTool(status);
        } else if (status === 'drag') {
            setAnnotationType(null);
        } else if (isAssistedLabelingStatus(status)) {
            resetDrawing();
        }
    });

    const activateBoundingBox = () => {
        if (annotationLabelContext.isOnAnnotationDetailsView) return;

        setStatus('bounding-box');
        setAnnotationType(AnnotationType.OBJECT_DETECTION);
        setAnnotationId(null);
        setLastCreatedAnnotationId(null);
    };

    const activateBrush = () => {
        if (!showSegmentationTool) return;

        setStatus('brush');
        setAnnotationType(AnnotationType.SEGMENTATION_MASK);
        if (!annotationLabelContext.isOnAnnotationDetailsView) setAnnotationId(null);
        setLastCreatedAnnotationId(null);
    };

    const activateSlic = (trigger: ToolbarTrigger) => {
        if (
            !showSegmentationTool ||
            !slicAvailable ||
            annotationLabelContext.isDrawing ||
            isPending
        )
            return;

        const shouldKeepSelectedAnnotation =
            annotationLabelContext.annotationId != null &&
            annotationLabelContext.annotationType === AnnotationType.SEGMENTATION_MASK;

        setStatus('slic');
        setAnnotationType(AnnotationType.SEGMENTATION_MASK);
        if (
            !annotationLabelContext.isOnAnnotationDetailsView &&
            (trigger === 'shortcut' || !shouldKeepSelectedAnnotation)
        ) {
            setAnnotationId(null);
        }
        setLastCreatedAnnotationId(null);
    };

    function onToolChange(tool: string, trigger: ToolbarTrigger) {
        switch (tool) {
            case 'cursor':
                setStatus('cursor');
                break;
            case 'drag':
                setStatus('drag');
                break;
            case 'bounding-box':
                activateBoundingBox();
                break;
            case 'brush':
                activateBrush();
                break;
            case 'slic':
                activateSlic(trigger);
                break;
            case 'smart-select':
            case 'find-instances':
                setStatus(tool);
                break;
        }
    }
</script>

<Toolbar
    {items}
    activeTool={sampleDetailsToolbarContext.status}
    {onToolChange}
    {shouldHandleShortcut}
/>
