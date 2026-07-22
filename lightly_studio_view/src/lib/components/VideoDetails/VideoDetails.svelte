<script lang="ts">
    import {
        Card,
        CardContent,
        MetadataSegment,
        SegmentTags,
        VideoDetailsNavigation,
        VideoFrameDetails,
        VideoPlayer
    } from '$lib/components';
    import {
        AnnotationType,
        type FrameView,
        type SampleView,
        type VideoView
    } from '$lib/api/lightly_studio_local';
    import { getVideoURLById, toVideoEvents, type VideoEvent } from '$lib/utils';
    import VideoSampleMetadata from '../VideoSampleMetadata/VideoSampleMetadata.svelte';
    import SampleDetailsCaptionSegment from '../SampleDetails/SampleDetailsCaptionsSegment/SampleDetailsCaptionSegment.svelte';
    import SelectClassDialog from '$lib/components/SelectClassDialog/SelectClassDialog.svelte';
    import { useVideoFrames } from '$lib/hooks/useVideoFrames/useVideoFrames';
    import { useVideoFrameAnnotations } from '$lib/hooks/useVideoFrameAnnotations/useVideoFrameAnnotations';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useUpdateAnnotationsMutation } from '$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
    import { useCreateLabel } from '$lib/hooks/useCreateLabel/useCreateLabel';
    import { useSelectClassDialog } from '$lib/hooks/useSelectClassDialog/useSelectClassDialog';
    import { onMount } from 'svelte';
    import { toast } from 'svelte-sonner';
    import { routeHelpers } from '$lib/routes';
    import VideoFrameAnnotationItem, {
        type PrerenderedAnnotation
    } from '../VideoFrameAnnotationItem/VideoFrameAnnotationItem.svelte';

    type VideoDetailsProps = {
        video: VideoView;
        datasetId: string;
        onVideoUpdate: () => void;
        frameNumber?: number;
    };
    const { video, datasetId, onVideoUpdate, frameNumber }: VideoDetailsProps = $props();

    let videoEl: HTMLVideoElement | null = $state(null);
    let frameRequestId: number | null = $state(null);

    // Imported events: classification annotations on the video carrying a time span.
    const videoEvents = $derived(toVideoEvents(video.sample.annotations ?? []));

    // Reuse the global "Edit annotations" toggle to enable event editing.
    const { isEditingMode } = useGlobalStorage();

    // Events live on the video's own collection; labels are shared per dataset.
    const eventCollectionId = (video.sample as SampleView)?.collection_id ?? datasetId;
    const { updateAnnotations } = useUpdateAnnotationsMutation({ collectionId: eventCollectionId });
    const { createAnnotation } = useCreateAnnotation({ collectionId: eventCollectionId });
    const { createLabel } = useCreateLabel({ collectionId: eventCollectionId });
    const annotationLabels = useAnnotationLabels(() => ({ collectionId: eventCollectionId }));

    const {
        open: selectClassOpen,
        requestLabel,
        handleConfirm: handleClassSelected,
        handleCancel: handleClassDialogCancel
    } = useSelectClassDialog();
    const labelNames = $derived(
        annotationLabels.data?.map((label) => label.annotation_label_name ?? '').filter(Boolean) ??
            []
    );

    async function handleEventResize(event: VideoEvent, startTimeS: number, endTimeS: number) {
        try {
            await updateAnnotations([
                {
                    annotation_id: event.id,
                    collection_id: event.annotationCollectionId,
                    start_time_s: startTimeS,
                    end_time_s: endTimeS
                }
            ]);
        } catch (error) {
            console.error('Failed to save event changes:', error);
            toast.error('Failed to save event changes. Please try again.');
        } finally {
            // Refetch either way so the timeline reflects the persisted span
            // (or reverts the optimistic preview if the update failed).
            onVideoUpdate();
        }
    }

    async function handleEventAdd(startTimeS: number, endTimeS: number) {
        const result = await requestLabel();
        if (!result?.label) return;

        try {
            let label = annotationLabels.data?.find(
                (item) => item.annotation_label_name === result.label
            );
            if (!label) {
                label = await createLabel({
                    dataset_id: datasetId,
                    annotation_label_name: result.label
                });
            }

            await createAnnotation({
                parent_sample_id: video.sample_id,
                annotation_type: AnnotationType.CLASSIFICATION,
                annotation_label_id: label.annotation_label_id!,
                start_time_s: startTimeS,
                end_time_s: endTimeS
            });
            onVideoUpdate();
            toast.success('Event created successfully');
        } catch (error) {
            toast.error('Failed to create event. Please try again.');
            console.error('Error creating event:', error);
        }
    }

    const {
        currentFrame,
        frames: videoFrames,
        loadFrameByPlaybackTime,
        loadFramesFromFrameNumber
    } = useVideoFrames({
        video
    });

    // Pre-render all frame annotations as dataURLs for efficient playback
    const frameAnnotationMap = $derived(
        useVideoFrameAnnotations({ frames: $videoFrames, imageWidth: video.width })
    );

    // Get prerendered annotations for current frame
    const prerenderedAnnotations = $derived.by((): PrerenderedAnnotation[] | undefined => {
        if (!$currentFrame) return undefined;
        return frameAnnotationMap.get($currentFrame.sample_id);
    });

    function stopFrameSyncLoop() {
        if (frameRequestId !== null) {
            cancelAnimationFrame(frameRequestId);
            frameRequestId = null;
        }
    }

    function startFrameSyncLoop() {
        stopFrameSyncLoop();

        const tick = () => {
            if (!videoEl) {
                frameRequestId = null;
                return;
            }

            void loadFrameByPlaybackTime(videoEl.currentTime, video.fps);
            frameRequestId = requestAnimationFrame(tick);
        };

        frameRequestId = requestAnimationFrame(tick);
    }

    const onplay = () => {
        startFrameSyncLoop();
    };

    const onpause = () => {
        stopFrameSyncLoop();
    };

    const onended = (event: Event) => {
        const target = event.target as HTMLVideoElement;
        void loadFrameByPlaybackTime(target.currentTime, video.fps);
        stopFrameSyncLoop();
    };

    const onseeked = (event: Event) => {
        const target = event.target as HTMLVideoElement;
        void loadFrameByPlaybackTime(target.currentTime, video.fps);
    };

    // null = waiting for the frame deep-link timestamp; 0 = start of video.
    let startTimeS = $state<number | null>(frameNumber !== undefined ? null : 0);

    // #key remounts on navigation, so onMount suffices; an $effect could re-fire
    // and stop the play sync loop.
    onMount(() => {
        if (frameNumber !== undefined) {
            void loadFramesFromFrameNumber(frameNumber);
        } else {
            void loadFrameByPlaybackTime(0, video.fps);
        }

        return () => stopFrameSyncLoop();
    });

    let videoFrameContainerEl: HTMLDivElement | null = $state(null);
    let videoWidth = $state(0);
    let videoHeight = $state(0);
    let overlayTop = $state(0);
    let overlayLeft = $state(0);

    let resizeObserver: ResizeObserver;

    // Align the annotation overlay to the <video> box, not the full player chrome.
    $effect(() => {
        if (!videoEl || !videoFrameContainerEl) return;

        const updateOverlaySize = () => {
            if (!videoEl || !videoFrameContainerEl) return;
            const videoRect = videoEl.getBoundingClientRect();
            const containerRect = videoFrameContainerEl.getBoundingClientRect();
            overlayLeft = videoRect.left - containerRect.left;
            overlayTop = videoRect.top - containerRect.top;
            videoWidth = videoRect.width;
            videoHeight = videoRect.height;
        };
        updateOverlaySize();

        resizeObserver = new ResizeObserver(updateOverlaySize);
        resizeObserver.observe(videoEl);
        resizeObserver.observe(videoFrameContainerEl);

        return () => resizeObserver.disconnect();
    });

    const getTimeByFrameNumber = (frame: FrameView) => {
        return frame.frame_timestamp_s + 0.002;
    };

    // Once the deep-linked frame loads, pass its timestamp to VideoPlayer.
    $effect(() => {
        if (frameNumber === undefined || startTimeS !== null || !$currentFrame) return;
        if ($currentFrame.frame_number !== frameNumber) return;
        startTimeS = getTimeByFrameNumber($currentFrame);
    });
</script>

<div class="flex h-full min-h-0 w-full flex-col">
    <div class="flex min-h-0 flex-1 gap-4">
        <Card className="flex h-full min-h-0 w-[60vw] flex-col overflow-hidden">
            <CardContent className="flex min-h-0 flex-1 flex-col overflow-hidden">
                <div
                    bind:this={videoFrameContainerEl}
                    class="video-frame-container relative min-h-0 flex-1 overflow-hidden rounded-lg bg-black"
                >
                    <VideoDetailsNavigation />
                    <VideoPlayer
                        src={getVideoURLById(video.sample_id)}
                        bind:videoEl
                        {startTimeS}
                        events={videoEvents}
                        durationS={video.duration_s ?? undefined}
                        editableEvents={$isEditingMode}
                        onEventResize={handleEventResize}
                        onEventAdd={handleEventAdd}
                        videoProps={{
                            muted: true,
                            class: 'object-contain',
                            onplay,
                            onpause,
                            onended,
                            onseeked
                        }}
                    />

                    {#if $currentFrame && videoWidth > 0}
                        <div
                            class="pointer-events-none absolute"
                            style={`top: ${overlayTop}px; left: ${overlayLeft}px; width: ${videoWidth}px; height: ${videoHeight}px;`}
                        >
                            <VideoFrameAnnotationItem
                                width={videoWidth}
                                height={videoHeight}
                                sample={$currentFrame}
                                showLabel={true}
                                sampleWidth={video.width}
                                sampleHeight={video.height}
                                {prerenderedAnnotations}
                            />
                        </div>
                    {/if}
                </div>
            </CardContent>
        </Card>

        <Card className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <CardContent className="h-full overflow-y-auto">
                {#if video?.sample?.sample_id}
                    <SegmentTags
                        tags={video.sample.tags ?? []}
                        collectionId={datasetId}
                        sampleId={video.sample.sample_id}
                        onRefetch={onVideoUpdate}
                    />
                {/if}
                <VideoSampleMetadata {video} />
                <MetadataSegment metadata_dict={(video?.sample as SampleView).metadata_dict} />
                {#if video?.sample?.sample_id}
                    <SampleDetailsCaptionSegment
                        refetch={onVideoUpdate}
                        captions={video?.sample?.captions ?? []}
                        sampleId={video?.sample?.sample_id}
                    />
                {/if}
                {#if $currentFrame}
                    {@const frameSample = $currentFrame.sample as SampleView}
                    {#if frameSample.collection_id && frameSample.sample_id}
                        {@const frameURL = routeHelpers.toFramesDetails(
                            datasetId,
                            'video_frame',
                            frameSample.collection_id,
                            frameSample.sample_id,
                            true
                        )}
                        <VideoFrameDetails frame={$currentFrame} {frameURL} />
                    {/if}
                {/if}
            </CardContent>
        </Card>
    </div>
</div>

<SelectClassDialog
    bind:open={$selectClassOpen}
    labels={labelNames}
    onConfirm={handleClassSelected}
    onCancel={handleClassDialogCancel}
/>

<style>
    .video-frame-container {
        width: 100%;
        min-height: 0;
    }
</style>
