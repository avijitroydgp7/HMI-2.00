from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtOpenGLWidgets import QOpenGLWidget


class AdvancedGraphicsView(QGraphicsView):
    """QGraphicsView configured for high-performance rendering."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Use an OpenGL viewport for hardware acceleration
        self.setViewport(QOpenGLWidget())

        flags = (
            QGraphicsView.OptimizationFlag.DontSavePainterState
            | QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing
        )
        self.setOptimizationFlags(flags)

        # Cache the view background to minimize repaints
        self.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)

        # Always update the full viewport for consistency with OpenGL rendering
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)