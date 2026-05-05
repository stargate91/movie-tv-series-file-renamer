from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont, QColor, QPainter, QPainterPath
from ui.v3.styles.theme import Theme

class PosterCarousel(QWidget):
    """A stacked poster widget that shows up to 3 layers for TV:
       Series poster (back) → Season poster (middle) → Episode still (front).
       For movies, just one poster is shown."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 440)
        self._posters = []   # list of QPixmap (up to 3)
        self._labels = []    # list of str labels
        self._current = 0    # which one is "active" / on top

    def set_single_poster(self, pixmap):
        """Movie mode: one poster, no carousel."""
        self._posters = [pixmap] if pixmap else []
        self._labels = ["Poster"]
        self._current = 0
        self.update()

    def set_tv_posters(self, series_pix=None, season_pix=None, *episode_pixs):
        """TV mode: layered posters for series/season, then all episode stills."""
        self._posters = []
        self._labels = []
        
        if series_pix and not series_pix.isNull():
            self._posters.append(series_pix)
            self._labels.append("Series")
            
        if season_pix and not season_pix.isNull():
            self._posters.append(season_pix)
            self._labels.append("Season")
            
        for i, ep_pix in enumerate(episode_pixs):
            if ep_pix and not ep_pix.isNull():
                self._posters.append(ep_pix)
                label = f"Episode {i+1}" if len(episode_pixs) > 1 else "Episode"
                self._labels.append(label)
                
        self._current = len(self._posters) - 1 if self._posters else 0
        self.update()

    def clear(self):
        self._posters = []
        self._labels = []
        self._current = 0
        self.update()

    def mousePressEvent(self, event):
        """Cycle through posters on click."""
        if len(self._posters) > 1:
            self._current = (self._current + 1) % len(self._posters)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w, h = self.width(), self.height()

        if not self._posters:
            # Empty state
            path = QPainterPath()
            path.addRoundedRect(0, 0, w, h, 12, 12)
            painter.setClipPath(path)
            painter.fillRect(0, 0, w, h, QColor(Theme.SURFACE))
            painter.setPen(QColor(Theme.TEXT_DIM))
            painter.setFont(QFont("Inter", 12, QFont.DemiBold))
            painter.drawText(0, 0, w, h, Qt.AlignCenter, "No Poster")
            return

        if len(self._posters) == 1:
            # Single poster mode (movies)
            path = QPainterPath()
            path.addRoundedRect(0, 0, w, h, 12, 12)
            painter.setClipPath(path)
            scaled = self._posters[0].scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (w - scaled.width()) // 2
            y = (h - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            return

        # Multi-poster stack mode (TV shows)
        total = len(self._posters)
        offset = 8  # pixel offset per card layer

        for i in range(total):
            # Draw from back to front, with active on top
            idx = (self._current - (total - 1 - i)) % total

            layer_offset = (total - 1 - i) * offset
            card_w = w - layer_offset * 2
            card_h = h - layer_offset * 2
            card_x = layer_offset
            card_y = layer_offset

            # Scale opacity for back cards
            opacity = 0.35 + 0.65 * (i / (total - 1)) if total > 1 else 1.0
            painter.setOpacity(opacity)

            path = QPainterPath()
            path.addRoundedRect(card_x, card_y, card_w, card_h, 12, 12)
            painter.setClipPath(path)

            # Shadow for depth
            if i < total - 1:
                painter.fillRect(card_x, card_y, card_w, card_h, QColor(0, 0, 0, 80))

            scaled = self._posters[idx].scaled(card_w, card_h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            px = card_x + (card_w - scaled.width()) // 2
            py = card_y + (card_h - scaled.height()) // 2
            painter.drawPixmap(px, py, scaled)

            painter.setClipping(False)

        # Draw label badge on the front card
        painter.setOpacity(1.0)
        label_text = self._labels[self._current] if self._current < len(self._labels) else ""
        if label_text and total > 1:
            font = QFont("Inter", 9, QFont.Bold)
            painter.setFont(font)
            fm = painter.fontMetrics()
            text_w = fm.horizontalAdvance(label_text) + 16
            text_h = 22

            badge_x = w - text_w - 8
            badge_y = 8

            badge_path = QPainterPath()
            badge_path.addRoundedRect(badge_x, badge_y, text_w, text_h, 6, 6)
            painter.fillPath(badge_path, QColor(0, 0, 0, 160))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(badge_x, badge_y, text_w, text_h, Qt.AlignCenter, label_text)

            # Dot indicators
            dot_y = h - 16
            dot_total_w = total * 12
            dot_start_x = (w - dot_total_w) // 2
            for di in range(total):
                cx = dot_start_x + di * 12 + 4
                if di == self._current:
                    painter.setBrush(QColor(Theme.PRIMARY))
                else:
                    painter.setBrush(QColor(255, 255, 255, 100))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(cx, dot_y, 6, 6)
