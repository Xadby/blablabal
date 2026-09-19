from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QFileDialog,
    QComboBox, QInputDialog, QMessageBox, QMenu, QAbstractItemView
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QAction
from library import SoundLibrary

class LibraryTab(QWidget):
    add_to_soundpad = pyqtSignal(dict)

    def __init__(self, library: SoundLibrary, parent=None):
        super().__init__(parent)
        self.library = library
        self._setup_ui()
        self._refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel(" Библиотека звуков Xadby Pad")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #e0e0e0;")
        header.addWidget(title)
        header.addStretch()

        self.count_label = QLabel("0 звуков")
        self.count_label.setStyleSheet("color: #888;")
        header.addWidget(self.count_label)
        layout.addLayout(header)

        filters = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск по имени и тегам...")
        self.search_input.textChanged.connect(self._refresh)
        filters.addWidget(self.search_input, 2)

        self.category_combo = QComboBox()
        self.category_combo.addItem("Все категории", "")
        self.category_combo.currentIndexChanged.connect(self._refresh)
        filters.addWidget(self.category_combo, 1)

        self.tag_combo = QComboBox()
        self.tag_combo.addItem("Все теги", "")
        self.tag_combo.currentIndexChanged.connect(self._refresh)
        filters.addWidget(self.tag_combo, 1)

        layout.addLayout(filters)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: #2b2b2b;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 4px;
                color: #e0e0e0;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #333;
            }
            QListWidget::item:selected {
                background: #3a5f8a;
            }
            QListWidget::item:hover {
                background: #333;
            }
        """)
        layout.addWidget(self.list_widget, 1)

        actions = QHBoxLayout()

        add_btn = QPushButton("➕ Добавить из файла")
        add_btn.clicked.connect(self._add_from_file)
        actions.addWidget(add_btn)

        add_to_pad_btn = QPushButton("🎯 Добавить в Xadby Pad")
        add_to_pad_btn.clicked.connect(self._add_selected_to_pad)
        actions.addWidget(add_to_pad_btn)

        actions.addStretch()

        export_btn = QPushButton("📤 Экспорт")
        export_btn.clicked.connect(self._export)
        actions.addWidget(export_btn)

        import_btn = QPushButton(" Импорт")
        import_btn.clicked.connect(self._import)
        actions.addWidget(import_btn)

        layout.addLayout(actions)

    def _refresh(self) -> None:
        current_cat = self.category_combo.currentData()
        current_tag = self.tag_combo.currentData()

        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("Все категории", "")
        for c in self.library.get_categories():
            self.category_combo.addItem(c, c)
        idx = self.category_combo.findData(current_cat)
        if idx >= 0:
            self.category_combo.setCurrentIndex(idx)
        self.category_combo.blockSignals(False)

        all_tags = set()
        for s in self.library.sounds:
            all_tags.update(s.get("tags", []))
        self.tag_combo.blockSignals(True)
        self.tag_combo.clear()
        self.tag_combo.addItem("Все теги", "")
        for t in sorted(all_tags):
            self.tag_combo.addItem(t, t)
        idx = self.tag_combo.findData(current_tag)
        if idx >= 0:
            self.tag_combo.setCurrentIndex(idx)
        self.tag_combo.blockSignals(False)

        query = self.search_input.text()
        category = self.category_combo.currentData() or ""
        tag = self.tag_combo.currentData() or ""

        results = self.library.search(query=query, category=category, tag=tag)

        self.list_widget.clear()
        for s in results:
            tags_str = ", ".join(s.get("tags", [])) if s.get("tags") else ""
            display = f"{s['name']}  [{s.get('category', '')}]"
            if tags_str:
                display += f"  🏷 {tags_str}"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, s)
            self.list_widget.addItem(item)

        self.count_label.setText(f"{len(self.library.sounds)} звуков")

    def _add_from_file(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Выберите звуковые файлы", "",
            "Звуковые файлы (*.mp3 *.wav *.ogg *.flac *.m4a);;Все файлы (*.*)"
        )
        if not files:
            return

        name, ok = QInputDialog.getText(self, "Имя звука", "Название (можно оставить пустым):")
        if not ok:
            return
        category, ok = QInputDialog.getText(self, "Категория", "Категория:", text="Без категории")
        if not ok:
            return
        tags_str, ok = QInputDialog.getText(self, "Теги", "Теги через запятую (необязательно):")
        if not ok:
            return
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

        for f in files:
            n = name if name and len(files) == 1 else ""
            self.library.add_sound(f, name=n, category=category, tags=tags)
        self._refresh()

    def _add_selected_to_pad(self) -> None:
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.information(self, "Инфо", "Выберите звук в списке")
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        self.add_to_soundpad.emit(data)

    def _on_double_click(self, item) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        self.add_to_soundpad.emit(data)

    def _show_context_menu(self, pos) -> None:
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        data = item.data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)

        use_action = QAction(" Добавить в Xadby Pad", self)
        use_action.triggered.connect(lambda: self.add_to_soundpad.emit(data))
        menu.addAction(use_action)

        rename_action = QAction("✏️ Переименовать", self)
        rename_action.triggered.connect(lambda: self._rename(data["id"], data["name"]))
        menu.addAction(rename_action)

        tags_action = QAction("🏷 Изменить теги", self)
        tags_action.triggered.connect(lambda: self._edit_tags(data["id"], data.get("tags", [])))
        menu.addAction(tags_action)

        menu.addSeparator()

        delete_action = QAction("🗑 Удалить", self)
        delete_action.triggered.connect(lambda: self._delete(data["id"]))
        menu.addAction(delete_action)

        menu.exec(self.list_widget.mapToGlobal(pos))

    def _rename(self, sound_id: str, current: str) -> None:
        new_name, ok = QInputDialog.getText(self, "Переименовать", "Новое имя:", text=current)
        if ok and new_name.strip():
            self.library.update_sound(sound_id, name=new_name.strip())
            self._refresh()

    def _edit_tags(self, sound_id: str, current_tags: list) -> None:
        text, ok = QInputDialog.getText(self, "Теги", "Теги через запятую:", text=", ".join(current_tags))
        if ok:
            tags = [t.strip() for t in text.split(",") if t.strip()]
            self.library.update_sound(sound_id, tags=tags)
            self._refresh()

    def _delete(self, sound_id: str) -> None:
        reply = QMessageBox.question(
            self, "Удалить", "Удалить звук из библиотеки?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.library.remove_sound(sound_id)
            self._refresh()

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт библиотеки", "xadby_pad_library.zip",
            "ZIP архив (*.zip)"
        )
        if not path:
            return
        try:
            self.library.export_to_zip(path)
            QMessageBox.information(self, "Успех", f"Библиотека экспортирована в:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт библиотеки", "", "ZIP архив (*.zip)"
        )
        if not path:
            return
        try:
            count = self.library.import_from_zip(path)
            QMessageBox.information(self, "Успех", f"Импортировано звуков: {count}")
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))