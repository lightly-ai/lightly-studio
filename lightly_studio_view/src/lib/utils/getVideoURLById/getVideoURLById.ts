import { PUBLIC_VIDEOS_MEDIA_URL } from '$env/static/public';

export const getVideoURLById = (videoId: string): string => `${PUBLIC_VIDEOS_MEDIA_URL}/${videoId}`;
