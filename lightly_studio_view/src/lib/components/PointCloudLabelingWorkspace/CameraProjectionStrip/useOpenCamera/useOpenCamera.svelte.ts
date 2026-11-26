import type { ChannelSummaryView } from '$lib/api/lightly_studio_local/types.gen';
import type { HistoryMode } from '../../workspaceOptions';
import {
    getAdjacentCamera,
    getCameraForDigit,
    type CameraDirection
} from '../cameraNavigation/cameraNavigation';

interface UseOpenCameraParams {
    getCameraChannels: () => ChannelSummaryView[];
    getSelectedChannelIds: () => number[];
    getOpenCamera: () => string | undefined;
    onOpenCameraChange: (camera: string | undefined, historyMode: HistoryMode) => void;
}

/** Selects the camera of the enlarged camera dialog from the selected camera channels. */
export function useOpenCamera({
    getCameraChannels,
    getSelectedChannelIds,
    getOpenCamera,
    onOpenCameraChange
}: UseOpenCameraParams) {
    const selectedChannels = $derived(
        getCameraChannels().filter((channel) =>
            getSelectedChannelIds().includes(channel.channel_id)
        )
    );
    const selectedNames = $derived(selectedChannels.map((channel) => channel.group_component_name));
    const openChannel = $derived(
        selectedChannels.find((channel) => channel.group_component_name === getOpenCamera())
    );

    // Channels load after the route, so an empty list is not a verdict on the open camera.
    $effect(() => {
        const openCamera = getOpenCamera();
        const isOpenCameraDeselected =
            openCamera !== undefined && !selectedNames.includes(openCamera);
        if (getCameraChannels().length > 0 && isOpenCameraDeselected) close();
    });

    function show(camera: string) {
        const openCamera = getOpenCamera();
        if (camera === openCamera) return;
        onOpenCameraChange(camera, openCamera === undefined ? 'push' : 'replace');
    }

    function close() {
        onOpenCameraChange(undefined, 'replace');
    }

    function switchCamera(direction: CameraDirection) {
        const openCamera = getOpenCamera();
        if (openCamera === undefined) return;
        const camera = getAdjacentCamera(selectedNames, openCamera, direction);
        if (camera !== undefined) onOpenCameraChange(camera, 'replace');
    }

    function handleWindowKeydown(event: KeyboardEvent) {
        const isInOtherDialog =
            event.target instanceof Element && event.target.closest('[role="dialog"]') !== null;
        if (getOpenCamera() === undefined && isInOtherDialog) return;
        const camera = getCameraForDigit(event, selectedNames);
        if (camera === undefined) return;
        event.preventDefault();
        show(camera);
    }

    return {
        get selectedChannels() {
            return selectedChannels;
        },
        get openChannel() {
            return openChannel;
        },
        /** 1-based position of the open camera, or 0 when no camera is open. */
        get position() {
            const openIndex = openChannel ? selectedChannels.indexOf(openChannel) : -1;
            return { index: openIndex + 1, total: selectedNames.length };
        },
        get canSwitch() {
            return selectedNames.length > 1;
        },
        show,
        close,
        switchCamera,
        handleWindowKeydown
    };
}
