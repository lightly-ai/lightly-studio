import type { ImageView, VideoView } from '$lib/api/lightly_studio_local';

export function isVideoView(view?: ImageView | VideoView | null): view is VideoView {
    return view?.type === 'video';
}
