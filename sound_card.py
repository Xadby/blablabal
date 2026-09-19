from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QFileDialog, QMenu, QSlider
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QAction
import os

class SoundCard(QWidget):
    play_requested = pyqtSignal(str, float)
    bind_requested = pyqtSignal(int)
    remove_requested = pyqtSignal(int)
    changed = pyqtSignal()

    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self.index = index
        self.file_path = ""
        self.hotkey = ""
        self.volume = 1.0
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("soundCard")
        self.setStyleSheet("""
            #soundCard {
                background-color: #2b2b2b;
                border: 1px solid #3c3c3c;
                border-radius: 8px;
                padding: 10px;
            }
            #soundCard:hover {
                border: 1px solid #5a5a5a;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.name_label = QLabel("Пустой слот")
        self.name_label.setStyleSheet("color: #e0e0e0; font-size: 13px; font-weight: 600;")
        self.name_label.setMinimumWidth(120)
        top_row.addWidget(self.name_label, 1)

        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(40, 32)
        self.play_btn.setToolTip("Воспроизвести")
        self.play_btn.clicked.connect(self._on_play)
        top_row.addWidget(self.play_btn)

        main_layout.addLayout(top_row)

        self.path_label = QLabel("Файл не выбран")
        self.path_label.setStyleSheet("color: #888; font-size: 11px;")
        self.path_label.setWordWrap(True)
        main_layout.addWidget(self.path_label)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

        self.hotkey_btn = QPushButton("Без бинда")
        self.hotkey_btn.setToolTip("Нажмите, чтобы назначить горячую клавишу")
        self.hotkey_btn.clicked.connect(lambda: self.bind_requested.emit(self.index))
        bottom_row.addWidget(self.hotkey_btn)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setToolTip(f"Громкость: 100%")
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        self.volume_slider.setFixedWidth(100)
        bottom_row.addWidget(self.volume_slider)

        main_layout.addLayout(bottom_row)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def set_data(self, file_path: str, hotkey: str, volume: float = 1.0) -> None:
        self.file_path = file_path
        self.hotkey = hotkey
        self.volume = volume
        self._update_display()

    def get_data(self) -> dict:
        return {
            "file_path": self.file_path,
            "hotkey": self.hotkey,
            "volume": self.volume,
        }

    def _update_display(self) -> None:
        if self.file_path:
            name = os.path.splitext(os.path.basename(self.file_path))[0]
            self.name_label.setText(name)
            self.path_label.setText(self.file_path)
            self.play_btn.setEnabled(True)
        else:
            self.name_label.setText("Пустой слот")
            self.path_label.setText("Файл не выбран")
            self.play_btn.setEnabled(False)

        self.hotkey_btn.setText(self.hotkey if self.hotkey else "Без бинда")
        self.volume_slider.setValue(int(self.volume * 100))

    def _on_play(self) -> None:
        if self.file_path:
            self.play_requested.emit(self.file_path, self.volume)

    def _on_volume_changed(self, value: int) -> None:
        self.volume = value / 100.0
        self.volume_slider.setToolTip(f"Громкость: {value}%")
        self.changed.emit()

    def _show_context_menu(self, pos) -> None:
        menu = QMenu(self)

        choose_action = QAction("Выбрать файл...", self)
        choose_action.triggered.connect(self._choose_file)
        menu.addAction(choose_action)

        clear_action = QAction("Очистить слот", self)
        clear_action.triggered.connect(self._clear_slot)
        menu.addAction(clear_action)

        menu.addSeparator()

        remove_action = QAction("Удалить", self)
        remove_action.triggered.connect(lambda: self.remove_requested.emit(self.index))
        menu.addAction(remove_action)

        menu.exec(self.mapToGlobal(pos))

    def _choose_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите звуковой файл",
            "",
            "Звуковые файлы (*.mp3 *.wav *.ogg *.flac *.m4a);;Все файлы (*.*)"
        )
        if file_path:
            self.file_path = file_path
            self._update_display()
            self.changed.emit()

    def _clear_slot(self) -> None:
        self.file_path = ""
        self.hotkey = ""
        self.volume = 1.0
        self._update_display()
        self.changed.emit()