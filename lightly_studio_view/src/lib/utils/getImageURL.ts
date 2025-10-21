import { PUBLIC_SAMPLES_URL } from '$env/static/public';

export const getImageURL = (imageID: string): string => `${PUBLIC_SAMPLES_URL}/sample/${imageID}`;
