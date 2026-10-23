<span
    data-testid="button-progress"
    role="progressbar"
    aria-label="Loading"
    class="bg-current/20 pointer-events-none absolute inset-x-0 bottom-0 h-0.5 overflow-hidden"
>
    <span class="button-progress-indicator absolute inset-y-0 bg-current"></span>
</span>

<style>
    .button-progress-indicator {
        animation: button-progress-slide 1.2s ease-in-out infinite;
    }
    @keyframes button-progress-slide {
        0% {
            left: -40%;
            width: 40%;
        }
        50% {
            left: 30%;
            width: 55%;
        }
        100% {
            left: 100%;
            width: 40%;
        }
    }
</style>
