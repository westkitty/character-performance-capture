"""Character Performance Capture UI Widgets."""

from cpc.ui.widgets.clean_preview_window import CleanPreviewWindow
from cpc.ui.widgets.command_palette import CommandPaletteDialog
from cpc.ui.widgets.command_preview import CommandPreviewWidget
from cpc.ui.widgets.model_selector import ModelSelectorWidget
from cpc.ui.widgets.panels import (
    AdvancedPanel,
    OutputsPanel,
    RendererPanel,
    SourcePanel,
    TrackerPanel,
)
from cpc.ui.widgets.preview_widget import PreviewWidget
from cpc.ui.widgets.telemetry_widget import TelemetryWidget

__all__ = [
    "AdvancedPanel",
    "CleanPreviewWindow",
    "CommandPaletteDialog",
    "CommandPreviewWidget",
    "ModelSelectorWidget",
    "OutputsPanel",
    "PreviewWidget",
    "RendererPanel",
    "SourcePanel",
    "TelemetryWidget",
    "TrackerPanel",
]
