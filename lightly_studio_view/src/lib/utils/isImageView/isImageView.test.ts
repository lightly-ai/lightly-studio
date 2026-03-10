import { isImageView } from './isImageView';
import type { ImageView, VideoView } from '$lib/api/lightly_studio_local';

describe('isImageView', () => {
	test('returns true for image view', () => {
		const imageView: ImageView = { type: 'image' } as ImageView;
		expect(isImageView(imageView)).toBe(true);
	});

	test('returns false for video view', () => {
		const videoView: VideoView = { type: 'video' } as VideoView;
		expect(isImageView(videoView)).toBe(false);
	});

	test('returns false for null', () => {
		expect(isImageView(null)).toBe(false);
	});

	test('returns false for undefined', () => {
		expect(isImageView(undefined)).toBe(false);
	});
});
