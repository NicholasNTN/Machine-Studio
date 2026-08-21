class VideoBackgroundRemovalService:
    """Optional AI matting boundary; no model is bundled with Machine Studio."""
    dependency_message = "AI Remove Background requires an optional local matting backend. Chroma Key is available now."

    @classmethod
    def available(cls): return False

    def submit(self, *_args, **_kwargs):
        raise RuntimeError(self.dependency_message)
