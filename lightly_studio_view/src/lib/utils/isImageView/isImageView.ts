import type { ImageView, VideoView } from '$lib/api/lightly_studio_local';

export function isImageView(view?: ImageView | VideoView | null): view is ImageView {
    return view?.type === 'image';
}
