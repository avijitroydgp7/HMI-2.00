# main_window/ui_setup.py
from PyQt6.QtWidgets import QStatusBar, QLabel, QWidget, QHBoxLayout, QFrame, QPushButton, QCheckBox
from PyQt6.QtCore import QByteArray, Qt
from utils.icon_manager import IconManager

from services.settings_service import settings_service

import qtawesome as qta

def setup_window(win):
    app_icon = qta.icon('fa5s.desktop')
    win.setWindowIcon(app_icon)
    win.resize(1600, 900)

def setup_status_bar(win):
    win.status_bar = QStatusBar()
    win.setStatusBar(win.status_bar)
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    
    def add_status_widget(icon_name, initial_text):
        layout.addWidget(_create_separator())
        icon_label = QLabel()
        icon_label.setPixmap(IconManager.create_pixmap(icon_name, 14))
        layout.addWidget(icon_label)
        text_label = QLabel(initial_text)
        layout.addWidget(text_label)
        return text_label
        
    win.active_area_label = add_status_widget('fa5s.bullseye', "None")
    win.object_name_label = add_status_widget('fa5s.i-cursor', "None")
    win.screen_dim_label = add_status_widget('fa5s.desktop', "W ----, H ----")
    win.object_size_label = add_status_widget('fa5s.ruler-combined', "W ----, H ----")
    win.object_pos_label = add_status_widget('fa5s.expand-arrows-alt', "X ----, Y ----")
    win.cursor_pos_label = add_status_widget('fa5s.mouse-pointer', "X ----, Y ----")
    layout.addWidget(_create_separator())
    
    # Zoom percentage (bottom-right)
    win.zoom_label = add_status_widget('fa5s.search-plus', "100%")
    layout.addWidget(_create_separator())
    win.status_bar.addPermanentWidget(container)

def setup_view_actions(win):
    tools_action = win.tools_toolbar.toggleViewAction()
    tools_action.setText("Tools Toolbar")
    tools_anim = IconManager.create_animated_icon('fa5s.tools')
    tools_action.setIcon(tools_anim.icon)
    tools_anim.add_target(tools_action)
    tools_action._animated_icon = tools_anim
    win.ribbon.add_view_action(tools_action)
    win.quick_access_toolbar.add_view_action(tools_action)

    drawing_action = win.drawing_toolbar.toggleViewAction()
    drawing_action.setText("Drawing Toolbar")
    drawing_anim = IconManager.create_animated_icon('fa5s.pencil-alt')
    drawing_action.setIcon(drawing_anim.icon)
    drawing_anim.add_target(drawing_action)
    drawing_action._animated_icon = drawing_anim
    win.ribbon.add_view_action(drawing_action)
    win.quick_access_toolbar.add_view_action(drawing_action)

    # Snapping controls
    win.snap_objects_cb = QCheckBox("Snap to Objects")
    win.snap_objects_cb.setChecked(settings_service.get_value("snap_to_objects", True))
    win.ribbon.view_tab.toolbar.addWidget(win.snap_objects_cb)
    win.snap_lines_cb = QCheckBox("Show Snap Lines")
    win.snap_lines_cb.setChecked(settings_service.get_value("snap_lines_visible", True))
    win.ribbon.view_tab.toolbar.addWidget(win.snap_lines_cb)
    win.ribbon.view_tab.toolbar.addSeparator()


    icon_map = {
        'project': 'fa5s.project-diagram', 'system': 'fa5s.cogs', 
        'screens': 'fa5.clone', 'properties': 'fa5s.list-ul',
        'resources': 'fa5s.box-open'
    }
    for name, dock in win.docks.items():
        action = dock.toggleViewAction()
        action.setText(name.capitalize())
        icon_name = icon_map.get(name)
        if icon_name:
            anim = IconManager.create_animated_icon(icon_name)
            action.setIcon(anim.icon)
            anim.add_target(action)
            action._animated_icon = anim
        win.ribbon.add_view_action(action)
        win.quick_access_toolbar.add_view_action(action)

def _create_separator():
    separator = QFrame()
    separator.setFrameShape(QFrame.Shape.VLine)
    return separator

def save_window_state(win):
    settings_service.set_value("main_window/geometry", win.saveGeometry().toHex().data().decode())
    settings_service.set_value("main_window/state", win.saveState().toHex().data().decode())
    settings_service.save()

def restore_window_state(win):
    geometry_hex = settings_service.get_value("main_window/geometry")
    if geometry_hex:
        win.restoreGeometry(QByteArray.fromHex(geometry_hex.encode()))
    state_hex = settings_service.get_value("main_window/state")
    if state_hex:
        win.restoreState(QByteArray.fromHex(state_hex.encode()))
