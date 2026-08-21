from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class PlaybackController(QObject):
    """Owns the complete Qt multimedia session and its Windows-safe reload path."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_player, self.main_output = self._pair()
        self.narration_player, self.narration_output = self._pair()
        self.music_player, self.music_output = self._pair()
        self.accompaniment_player, self.accompaniment_output = self._pair()

    def _pair(self):
        player = QMediaPlayer(self)
        output = QAudioOutput(self)
        player.setAudioOutput(output)
        return player, output

    def detach_narration(self):
        self.narration_player.stop()
        self.narration_player.setSource(QUrl())
        self.narration_player.setAudioOutput(None)

    def rebuild_narration(self, source, *, volume, muted, status_callback=None):
        """Discard stale Windows media/audio objects before loading generated audio."""
        old_player, old_output = self.narration_player, self.narration_output
        old_player.stop(); old_player.setSource(QUrl()); old_player.setAudioOutput(None)
        player, output = self._pair()
        output.setVolume(max(0.0, min(1.0, float(volume))))
        output.setMuted(bool(muted))
        if status_callback is not None:
            player.mediaStatusChanged.connect(status_callback)
        path = Path(str(source or ""))
        player.setSource(QUrl.fromLocalFile(str(path.resolve())) if path.exists() and path.stat().st_size > 0 else QUrl())
        self.narration_player, self.narration_output = player, output
        old_player.deleteLater(); old_output.deleteLater()
        return player, output

    def narration_diagnostics(self):
        source = self.narration_player.source().toLocalFile() if self.narration_player.source().isLocalFile() else ""
        path = Path(source) if source else None
        return {
            "source": source,
            "exists": bool(path and path.exists()),
            "size": path.stat().st_size if path and path.exists() else 0,
            "player": bool(self.narration_player),
            "output": self.narration_player.audioOutput() is self.narration_output,
            "muted": self.narration_output.isMuted(),
            "volume": self.narration_output.volume(),
            "media_status": self.narration_player.mediaStatus(),
            "playback_state": self.narration_player.playbackState(),
        }
