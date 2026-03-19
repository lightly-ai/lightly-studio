<script module>
	import { defineMeta } from '@storybook/addon-svelte-csf';
	import VideoSampleMetadata from './VideoSampleMetadata.svelte';

	const { Story } = defineMeta({
		title: 'Components/VideoSampleMetadata',
		component: VideoSampleMetadata,
		tags: ['autodocs']
	});
</script>

<Story
	name="Default"
	args={{
		video: {
			file_name: 'sample_video.mp4',
			width: 1920,
			height: 1080,
			duration_s: 45.5,
			fps: 30.0
		}
	}}
/>

<Story
	name="Long Filename"
	args={{
		video: {
			file_name:
				'very_long_filename_that_should_wrap_or_break_properly_in_the_metadata_panel_to_test_overflow_behavior.mp4',
			width: 1920,
			height: 1080,
			duration_s: 45.5,
			fps: 30.0
		}
	}}
/>

<Story
	name="Zero Duration"
	args={{
		video: {
			file_name: 'zero_duration.mp4',
			width: 1920,
			height: 1080,
			duration_s: 0,
			fps: 30.0
		}
	}}
/>

<Story
	name="Null Duration"
	args={{
		video: {
			file_name: 'no_duration.mp4',
			width: 1920,
			height: 1080,
			duration_s: null,
			fps: 30.0
		}
	}}
/>

<Story
	name="High FPS"
	args={{
		video: {
			file_name: 'high_fps.mp4',
			width: 3840,
			height: 2160,
			duration_s: 120.75,
			fps: 120.0
		}
	}}
/>
