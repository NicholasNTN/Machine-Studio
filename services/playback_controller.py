from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


def narration_status_action(generation, current_generation, player, current_player,
                            output, current_output, *, restoring=False, switching=False):
    """Return the only safe action for a narration-session status signal."""
    if (generation != current_generation or player is not current_player or
            output is not current_output):
        return "ignore"
    if restoring or switching:
        return "defer"
    return "apply"


class PlaybackController(QObject):
    """Owns the complete Qt multimedia session and its Windows-safe reload path."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_player, self.main_output = self._pair()
        self.narration_player, self.narration_output = self._pair()
        self.narration_generation = 0
        self._narration_status_slot = None
        self.music_player, self.music_output = self._pair()
        self.accompaniment_player, self.accompaniment_output = self._pair()

    def _pair(self):
        player = QMediaPlayer(self)
        output = QAudioOutput(self)
        player.setAudioOutput(output)
        return player, output

    def detach_narration(self):
        self.narration_generation += 1
        if self._narration_status_slot is not None:
            try:
                self.narration_player.mediaStatusChanged.disconnect(self._narration_status_slot)
            except (RuntimeError, TypeError):
                pass
            self._narration_status_slot = None
        self.narration_player.stop()
        self.narration_player.setSource(QUrl())
        self.narration_player.setAudioOutput(None)

    def rebuild_narration(self, source, *, volume, muted, status_callback=None):
        """Install a new narration session before asynchronously loading its source."""
        old_player, old_output = self.narration_player, self.narration_output
        if self._narration_status_slot is not None:
            try:
                old_player.mediaStatusChanged.disconnect(self._narration_status_slot)
            except (RuntimeError, TypeError):
                pass
            self._narration_status_slot = None
        old_player.stop()
        old_player.setSource(QUrl())
        old_player.setAudioOutput(None)
        player, output = self._pair()
        output.setVolume(max(0.0, min(1.0, float(volume))))
        output.setMuted(bool(muted))
        self.narration_generation += 1
        generation = self.narration_generation
        self.narration_player, self.narration_output = player, output
        if status_callback is not None:
            self._narration_status_slot = (
                lambda status, p=player, out=output, gen=generation:
                    status_callback(p, out, gen, status)
            )
            player.mediaStatusChanged.connect(self._narration_status_slot)
        path = Path(str(source or ""))
        url = QUrl.fromLocalFile(str(path.resolve())) if path.exists() and path.stat().st_size > 0 else QUrl()

        def load_current_session():
            if generation != self.narration_generation or player is not self.narration_player:
                return
            player.setSource(url)

        # Windows may emit mediaStatusChanged synchronously from setSource().
        # Defer it until MainWindow has installed the returned session references.
        QTimer.singleShot(0, load_current_session)
        old_player.deleteLater()
        old_output.deleteLater()
        return player, output, generation

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
