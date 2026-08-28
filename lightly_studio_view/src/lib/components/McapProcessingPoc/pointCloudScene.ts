import type { BufferGeometry, PerspectiveCamera, Points, Scene, WebGLRenderer } from 'three';
import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

export class PointCloudScene {
    private constructor(
        private readonly THREE: typeof import('three'),
        private readonly scene: Scene,
        private readonly camera: PerspectiveCamera,
        private readonly renderer: WebGLRenderer,
        private readonly controls: OrbitControls,
        private points?: Points
    ) {}

    static async create(container: HTMLElement): Promise<PointCloudScene> {
        const THREE = await import('three');
        const { OrbitControls } = await import('three/examples/jsm/controls/OrbitControls.js');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color('#07111f');
        const camera = new THREE.PerspectiveCamera(55, 1, 0.05, 10_000);
        camera.up.set(0, 0, 1);
        camera.position.set(12, -12, 8);
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        container.appendChild(renderer.domElement);
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        scene.add(new THREE.AxesHelper(2));
        const grid = new THREE.GridHelper(100, 50, '#334155', '#1e293b');
        grid.rotateX(Math.PI / 2);
        scene.add(grid);
        const instance = new PointCloudScene(THREE, scene, camera, renderer, controls);
        instance.resize(container.clientWidth, container.clientHeight);
        instance.animate();
        return instance;
    }

    setPoints(values: Float32Array): void {
        this.removePoints();
        const count = values.length / 4;
        const positions = new Float32Array(count * 3);
        const colors = new Float32Array(count * 3);
        const intensities = intensityRange(values);
        for (let index = 0; index < count; index += 1) {
            positions.set(values.subarray(index * 4, index * 4 + 3), index * 3);
            const color = normalize(values[index * 4 + 3], intensities);
            colors.set([color, color, color], index * 3);
        }
        const geometry = new this.THREE.BufferGeometry();
        geometry.setAttribute('position', new this.THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new this.THREE.BufferAttribute(colors, 3));
        geometry.computeBoundingSphere();
        const radius = geometry.boundingSphere?.radius ?? 10;
        const material = new this.THREE.PointsMaterial({
            size: Math.max(radius / 250, 0.04),
            vertexColors: true
        });
        this.points = new this.THREE.Points(geometry, material);
        this.scene.add(this.points);
        this.fitCamera(geometry);
    }

    resize(width: number, height: number): void {
        if (width === 0 || height === 0) return;
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height, false);
    }

    dispose(): void {
        this.removePoints();
        this.controls.dispose();
        this.renderer.dispose();
        this.renderer.domElement.remove();
    }

    private fitCamera(geometry: BufferGeometry): void {
        const sphere = geometry.boundingSphere;
        if (!sphere) return;
        this.controls.target.copy(sphere.center);
        const distance = Math.max(sphere.radius * 1.7, 2);
        this.camera.position.set(
            sphere.center.x + distance,
            sphere.center.y - distance,
            sphere.center.z + distance * 0.65
        );
        this.camera.far = Math.max(distance * 10, 1000);
        this.camera.updateProjectionMatrix();
        this.controls.update();
    }

    private removePoints(): void {
        if (!this.points) return;
        this.scene.remove(this.points);
        this.points.geometry.dispose();
        const material = this.points.material;
        if (Array.isArray(material)) material.forEach((item) => item.dispose());
        else material.dispose();
        this.points = undefined;
    }

    private animate = (): void => {
        if (!this.renderer.domElement.isConnected) return;
        requestAnimationFrame(this.animate);
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    };
}

function intensityRange(values: Float32Array): [number, number] {
    let minimum = Number.POSITIVE_INFINITY;
    let maximum = Number.NEGATIVE_INFINITY;
    for (let index = 3; index < values.length; index += 4) {
        minimum = Math.min(minimum, values[index]);
        maximum = Math.max(maximum, values[index]);
    }
    return [minimum, maximum];
}

function normalize(value: number, [minimum, maximum]: [number, number]): number {
    if (!Number.isFinite(value) || maximum <= minimum) return 0.8;
    return 0.15 + (0.85 * (value - minimum)) / (maximum - minimum);
}
