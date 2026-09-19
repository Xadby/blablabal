from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QScrollArea, QGridLayout,
    QSlider, QSystemTrayIcon, QMenu, QTabWidget,
    QComboBox, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction
from config import Config
from audio_player import AudioPlayer
from hotkey_manager import HotkeyManager
from library import SoundLibrary
from sound_card import SoundCard
from library_tab import LibraryTab
import os


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Xadby Pad v2.0")
        self.setMinimumSize(1000, 650)
        self.resize(1100, 750)

        self.config = Config()
        self.player = AudioPlayer()
        self.hotkey_manager = HotkeyManager()
        self.library = SoundLibrary()
        self.cards = []

        self._is_listening_for_hotkey = False
        self._hotkey_target_index = -1
        self._pressed_keys = set()

        self._setup_ui()
        self._setup_tray()
        self._load_devices()
        self._load_sounds()
        self._apply_settings()

        self.hotkey_manager.start()

    # =========================================================
    # UI
    # =========================================================
    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Шапка
        header = QHBoxLayout()
        title = QLabel("🎵 Xadby Pad")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #e0e0e0;")
        header.addWidget(title)
        header.addStretch()

        header.addWidget(QLabel("Громкость:"))
        self.master_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.master_volume_slider.setRange(0, 100)
        self.master_volume_slider.setValue(100)
        self.master_volume_slider.setFixedWidth(150)
        self.master_volume_slider.valueChanged.connect(self._on_master_volume_changed)
        header.addWidget(self.master_volume_slider)

        main_layout.addLayout(header)

        # Панель устройств
        devices_row = QHBoxLayout()

        devices_row.addWidget(QLabel("🔊 Вывод:"))
        self.primary_device_combo = QComboBox()
        self.primary_device_combo.addItem("По умолчанию (системный)", None)
        self.primary_device_combo.currentIndexChanged.connect(self._on_primary_device_changed)
        devices_row.addWidget(self.primary_device_combo, 1)

        devices_row.addWidget(QLabel("🎙 Дублировать в:"))
        self.mirror_device_combo = QComboBox()
        self.mirror_device_combo.addItem("Не дублировать", None)
        self.mirror_device_combo.currentIndexChanged.connect(self._on_mirror_device_changed)
        devices_row.addWidget(self.mirror_device_combo, 1)

        stop_btn = QPushButton("⏹ Стоп")
        stop_btn.clicked.connect(self.player.stop_all)
        devices_row.addWidget(stop_btn)

        main_layout.addLayout(devices_row)

        # Вкладки
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #3c3c3c; border-radius: 4px; padding: 8px; }
            QTabBar::tab {
                background: #2b2b2b; color: #ccc; padding: 8px 18px;
                border: 1px solid #3c3c3c; border-bottom: none;
                border-top-left-radius: 4px; border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected { background: #3a5f8a; color: white; }
            QTabBar::tab:hover { background: #333; }
        """)

        # Вкладка 1: SoundPad
        pad_widget = QWidget()
        pad_layout = QVBoxLayout(pad_widget)
        pad_layout.setContentsMargins(0, 0, 0, 0)

        actions_row = QHBoxLayout()
        add_btn = QPushButton("➕ Добавить звук")
        add_btn.clicked.connect(self._add_sound)
        actions_row.addWidget(add_btn)

        clear_btn = QPushButton("🗑 Очистить все слоты")
        clear_btn.clicked.connect(self._clear_all_sounds)
        actions_row.addWidget(clear_btn)

        actions_row.addStretch()

        self.status_label = QLabel("Готово")
        self.status_label.setStyleSheet("color: #888; font-size: 12px;")
        actions_row.addWidget(self.status_label)

        pad_layout.addLayout(actions_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cards_container = QWidget()
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setSpacing(12)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(self.cards_container)
        pad_layout.addWidget(scroll, 1)

        self.tabs.addTab(pad_widget, "🎛 Xadby Pad")

        # Вкладка 2: Библиотека
        self.library_tab = LibraryTab(self.library)
        self.library_tab.add_to_soundpad.connect(self._add_from_library)
        self.tabs.addTab(self.library_tab, "📚 Библиотека")

        main_layout.addWidget(self.tabs, 1)

    # =========================================================
    # Трей
    # =========================================================
    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("Xadby Pad")
        tray_menu = QMenu()
        show_action = QAction("Показать", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self._quit)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()

    def closeEvent(self, event) -> None:
        if self.config.get_setting("minimize_to_tray", True) and hasattr(self, "tray_icon"):
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Xadby Pad", "Свёрнуто в трей. Хоткеи работают.",
                QSystemTrayIcon.MessageIcon.Information, 2000,
            )
        else:
            self._quit()

    def _quit(self) -> None:
        self.hotkey_manager.stop()
        self.player.quit()
        QApplication.quit()

    # =========================================================
    # Устройства
    # =========================================================
    def _load_devices(self) -> None:
        devices = self.player.get_output_devices()
        for dev_id, name, _ in devices:
            self.primary_device_combo.addItem(name, dev_id)
            self.mirror_device_combo.addItem(name, dev_id)

        saved_primary = self.config.get_setting("primary_device")
        saved_mirror = self.config.get_setting("mirror_device")
        if saved_primary is not None:
            idx = self.primary_device_combo.findData(saved_primary)
            if idx >= 0:
                self.primary_device_combo.setCurrentIndex(idx)
        if saved_mirror is not None:
            idx = self.mirror_device_combo.findData(saved_mirror)
            if idx >= 0:
                self.mirror_device_combo.setCurrentIndex(idx)

    def _on_primary_device_changed(self, index: int) -> None:
        dev_id = self.primary_device_combo.currentData()
        self.player.set_primary_device(dev_id)
        self.config.set_setting("primary_device", dev_id)

    def _on_mirror_device_changed(self, index: int) -> None:
        dev_id = self.mirror_device_combo.currentData()
        self.player.set_mirror_device(dev_id)
        self.config.set_setting("mirror_device", dev_id)

    # =========================================================
    # Карточки
    # =========================================================
    def _add_sound(self) -> None:
        card = SoundCard(len(self.cards))
        card.play_requested.connect(self._on_play)
        card.bind_requested.connect(self._start_hotkey_capture)
        card.remove_requested.connect(self._remove_sound)
        card.changed.connect(self._save_sounds)
        self.cards.append(card)
        self._rearrange_cards()
        self._save_sounds()

    def _add_from_library(self, entry: dict) -> None:
        card = SoundCard(len(self.cards))
        card.play_requested.connect(self._on_play)
        card.bind_requested.connect(self._start_hotkey_capture)
        card.remove_requested.connect(self._remove_sound)
        card.changed.connect(self._save_sounds)
        card.set_data(file_path=entry["file"], hotkey="", volume=1.0)
        self.cards.append(card)
        self._rearrange_cards()
        self._save_sounds()
        self.tabs.setCurrentIndex(0)
        self.status_label.setText(f"✓ Добавлено из библиотеки: {entry['name']}")

    def _remove_sound(self, index: int) -> None:
        if 0 <= index < len(self.cards):
            card = self.cards[index]
            if card.hotkey:
                hk = HotkeyManager.parse_hotkey_string(card.hotkey)
                self.hotkey_manager.unbind(hk)
            card.setParent(None)
            card.deleteLater()
            self.cards.pop(index)
            for i, c in enumerate(self.cards):
                c.index = i
            self._rearrange_cards()
            self._save_sounds()

    def _clear_all_sounds(self) -> None:
        for card in self.cards:
            if card.hotkey:
                hk = HotkeyManager.parse_hotkey_string(card.hotkey)
                self.hotkey_manager.unbind(hk)
            card.setParent(None)
            card.deleteLater()
        self.cards.clear()
        self._rearrange_cards()
        self._save_sounds()

    def _rearrange_cards(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        columns = 3
        for i, card in enumerate(self.cards):
            self.cards_layout.addWidget(card, i // columns, i % columns)

    def _on_play(self, file_path: str, volume: float) -> None:
        ok = self.player.play(file_path, volume)
        if ok:
            name = os.path.basename(file_path)
            self.status_label.setText(f"▶ {name}")
            QTimer.singleShot(3000, lambda: self.status_label.setText("Готово"))

    # =========================================================
    # Хоткеи
    # =========================================================
    def _start_hotkey_capture(self, index: int) -> None:
        if self._is_listening_for_hotkey:
            return
        self._is_listening_for_hotkey = True
        self._hotkey_target_index = index
        self._pressed_keys.clear()
        self.status_label.setText("⌨ Нажмите сочетание клавиш...")
        self.hotkey_manager.set_enabled(False)
        QApplication.instance().installEventFilter(self)

    def _finish_hotkey_capture(self) -> None:
        self._is_listening_for_hotkey = False
        self.hotkey_manager.set_enabled(True)
        QApplication.instance().removeEventFilter(self)
        self.status_label.setText("Готово")

    def eventFilter(self, obj, event):
        if self._is_listening_for_hotkey:
            from PyQt6.QtCore import QEvent
            if event.type() == QEvent.Type.KeyPress:
                key = event.key()
                key_name = self._qt_key_to_name(key)
                if key_name:
                    self._pressed_keys.add(key_name)
                    hotkey_str = "+".join(sorted(self._pressed_keys))
                    self._bind_hotkey(self._hotkey_target_index, hotkey_str)
                    self._finish_hotkey_capture()
                    return True
        return super().eventFilter(obj, event)

    def _qt_key_to_name(self, key) -> str:
        from PyQt6.QtCore import Qt as QtConst
        key_map = {
            QtConst.Key.Key_F1: "f1", QtConst.Key.Key_F2: "f2", QtConst.Key.Key_F3: "f3",
            QtConst.Key.Key_F4: "f4", QtConst.Key.Key_F5: "f5", QtConst.Key.Key_F6: "f6",
            QtConst.Key.Key_F7: "f7", QtConst.Key.Key_F8: "f8", QtConst.Key.Key_F9: "f9",
            QtConst.Key.Key_F10: "f10", QtConst.Key.Key_F11: "f11", QtConst.Key.Key_F12: "f12",
            QtConst.Key.Key_Space: "space", QtConst.Key.Key_Return: "enter",
            QtConst.Key.Key_Escape: "escape", QtConst.Key.Key_Backspace: "backspace",
            QtConst.Key.Key_Tab: "tab", QtConst.Key.Key_CapsLock: "capslock",
        }
        name = key_map.get(key)
        if name is None and QtConst.Key.Key_A <= key <= QtConst.Key.Key_Z:
            name = chr(key).lower()
        elif name is None and QtConst.Key.Key_0 <= key <= QtConst.Key.Key_9:
            name = chr(key)
        return name

    def _bind_hotkey(self, index: int, hotkey_str: str) -> None:
        if index < 0 or index >= len(self.cards):
            return
        card = self.cards[index]
        if card.hotkey:
            old_hk = HotkeyManager.parse_hotkey_string(card.hotkey)
            self.hotkey_manager.unbind(old_hk)
        card.hotkey = hotkey_str
        card._update_display()
        hk = HotkeyManager.parse_hotkey_string(hotkey_str)
        self.hotkey_manager.bind(hk, lambda i=index: self._on_hotkey_triggered(i))
        self._save_sounds()
        self.status_label.setText(f"✓ Бинд: {hotkey_str}")

    def _on_hotkey_triggered(self, index: int) -> None:
        if 0 <= index < len(self.cards):
            card = self.cards[index]
            if card.file_path:
                self.player.play(card.file_path, card.volume)

    # =========================================================
    # Настройки и сохранение
    # =========================================================
    def _on_master_volume_changed(self, value: int) -> None:
        self.player.set_master_volume(value / 100.0)
        self.config.set_setting("master_volume", value / 100.0)

    def _load_sounds(self) -> None:
        for s in self.config.get_sounds():
            card = SoundCard(len(self.cards))
            card.play_requested.connect(self._on_play)
            card.bind_requested.connect(self._start_hotkey_capture)
            card.remove_requested.connect(self._remove_sound)
            card.changed.connect(self._save_sounds)
            card.set_data(
                file_path=s.get("file_path", ""),
                hotkey=s.get("hotkey", ""),
                volume=s.get("volume", 1.0),
            )
            if card.hotkey and card.file_path:
                hk = HotkeyManager.parse_hotkey_string(card.hotkey)
                current_index = len(self.cards)
                self.hotkey_manager.bind(hk, lambda i=current_index: self._on_hotkey_triggered(i))
            self.cards.append(card)
        self._rearrange_cards()

    def _save_sounds(self) -> None:
        self.config.set_sounds([c.get_data() for c in self.cards])

    def _apply_settings(self) -> None:
        vol = self.config.get_setting("master_volume", 1.0)
        self.master_volume_slider.setValue(int(vol * 100))
        self.player.set_master_volume(vol)