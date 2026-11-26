import type { HistoryMode, WorkspaceOptions } from '../workspaceOptions';

type OpenCameraOptions = Pick<WorkspaceOptions, 'openCamera' | 'onOpenCameraChange'>;

/**
 * Gives the open camera of the enlarged camera dialog.
 *
 * A host that passes `onOpenCameraChange` owns the open camera, for example in its URL. Without
 * it, the workspace keeps the open camera itself, so the dialog works in every configuration.
 */
export function useOpenCameraState(getOptions: () => OpenCameraOptions) {
    let localOpenCamera = $state<string | undefined>();

    return {
        get openCamera() {
            const { openCamera, onOpenCameraChange } = getOptions();
            return onOpenCameraChange ? openCamera : localOpenCamera;
        },
        setOpenCamera(camera: string | undefined, historyMode: HistoryMode) {
            const { onOpenCameraChange } = getOptions();
            if (onOpenCameraChange) onOpenCameraChange(camera, historyMode);
            else localOpenCamera = camera;
        }
    };
}
