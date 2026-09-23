import type { ImageView, McapView, VideoView } from '$lib/api/lightly_studio_local';

export function isImageView(view?: ImageView | VideoView | McapView | null): view is ImageView {
    return view?.type === 'image';
}
