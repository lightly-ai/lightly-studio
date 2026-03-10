import { isVideoView } from './isVideoView';
import type { ImageView, VideoView } from '$lib/api/lightly_studio_local';

describe('isVideoView', () => {
	test('returns true for video view', () => {
		const videoView: VideoView = { type: 'video' } as VideoView;
		expect(isVideoView(videoView)).toBe(true);
	});

	test('returns false for image view', () => {
		const imageView: ImageView = { type: 'image' } as ImageView;
		expect(isVideoView(imageView)).toBe(false);
	});

	test('returns false for null', () => {
		expect(isVideoView(null)).toBe(false);
	});

	test('returns false for undefined', () => {
		expect(isVideoView(undefined)).toBe(false);
	});
});
