import { PUBLIC_VIDEOS_MEDIA_URL } from '$env/static/public';
import { withProxyMediaMode } from '../mediaRecovery';

interface GetVideoURLOptions {
    mode?: 'proxy';
}

export const getVideoURLById = (videoId: string, options: GetVideoURLOptions = {}): string => {
    const url = `${PUBLIC_VIDEOS_MEDIA_URL}/${videoId}`;
    return options.mode === 'proxy' ? withProxyMediaMode(url) : url;
};
