import sys
import os
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QScrollArea, QFrame, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QColor, QPalette

from preprocessor import preprocess_image
from extractor import extract_text, parse_receipt
from exporter import export_csv


# ─────────────────────────────────────────────
# Worker thread : traitement OCR en arrière-plan
# ─────────────────────────────────────────────
class OcrWorker(QThread):
    progress = pyqtSignal(int, str)       # (index, nom fichier)
    finished = pyqtSignal(list, str)      # (results, csv_path)
    error = pyqtSignal(str)

    def __init__(self, image_paths: list[str]):
        super().__init__()
        self.image_paths = image_paths

    def run(self):
        results = []
        total = len(self.image_paths)

        for i, img_path in enumerate(self.image_paths):
            filename = os.path.basename(img_path)
            self.progress.emit(i, filename)

            try:
                processed = preprocess_image(img_path)
                text = extract_text(processed)
                data = parse_receipt(text)
                data["fichier"] = filename
                results.append(data)
            except Exception as e:
                results.append({
                    "fichier": filename,
                    "prix_ttc": None,
                    "tva": None,
                    "adresse": None,
                })

        try:
            csv_path = export_csv(results)
            self.finished.emit(results, csv_path)
        except Exception as e:
            self.error.emit(str(e))


# ─────────────────────────────────────────────
# Zone de drag & drop
# ─────────────────────────────────────────────
class DropZone(QFrame):
    files_dropped = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(200)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #555;
                border-radius: 12px;
                background-color: #1e1e1e;
            }
            DropZone:hover {
                border-color: #4fc3f7;
                background-color: #1a2a35;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("📂")
        icon.setFont(QFont("Segoe UI Emoji", 36))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel("Glisse tes tickets ici\nou clique pour sélectionner")
        self.label.setFont(QFont("Segoe UI", 13))
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #aaa;")

        layout.addWidget(icon)
        layout.addWidget(self.label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                DropZone {
                    border: 2px dashed #4fc3f7;
                    border-radius: 12px;
                    background-color: #1a2a35;
                }
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #555;
                border-radius: 12px;
                background-color: #1e1e1e;
            }
            DropZone:hover {
                border-color: #4fc3f7;
                background-color: #1a2a35;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #555;
                border-radius: 12px;
                background-color: #1e1e1e;
            }
            DropZone:hover {
                border-color: #4fc3f7;
                background-color: #1a2a35;
            }
        """)
        extensions = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif")
        paths = [
            url.toLocalFile() for url in event.mimeData().urls()
            if url.toLocalFile().lower().endswith(extensions)
        ]
        if paths:
            self.files_dropped.emit(paths)

    def mousePressEvent(self, event):
        self.files_dropped.emit([])  # Signal vide = ouvrir dialog


# ─────────────────────────────────────────────
# Ligne de résultat
# ─────────────────────────────────────────────
class ResultRow(QFrame):
    def __init__(self, data: dict):
        super().__init__()
        self.setStyleSheet("""
            ResultRow {
                background-color: #252525;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        def cell(text, color="#ddd", bold=False, width=None):
            lbl = QLabel(text or "—")
            font = QFont("Segoe UI", 10)
            font.setBold(bold)
            lbl.setFont(font)
            lbl.setStyleSheet(f"color: {color};")
            if width:
                lbl.setFixedWidth(width)
            return lbl

        fichier = data.get("fichier", "")
        ttc = data.get("prix_ttc")
        tva = data.get("tva")
        adresse = data.get("adresse")

        layout.addWidget(cell(fichier, "#aaa", width=200))
        layout.addWidget(cell(f"{ttc} €" if ttc else None, "#4fc3f7", bold=True, width=90))
        layout.addWidget(cell(f"{tva} €" if tva else None, "#81c784", width=80))
        layout.addWidget(cell(adresse, "#ddd"))


# ─────────────────────────────────────────────
# Fenêtre principale
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Receipt Reader")
        self.setMinimumSize(800, 600)
        self.image_paths = []
        self.worker = None

        self._build_ui()
        self._apply_theme()

    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #141414;
                color: #ddd;
            }
            QPushButton {
                background-color: #4fc3f7;
                color: #000;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #81d4fa;
            }
            QPushButton:disabled {
                background-color: #333;
                color: #666;
            }
            QPushButton#btn_secondary {
                background-color: #252525;
                color: #aaa;
                border: 1px solid #444;
            }
            QPushButton#btn_secondary:hover {
                background-color: #2f2f2f;
                color: #ddd;
            }
            QProgressBar {
                background-color: #252525;
                border-radius: 4px;
                height: 6px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4fc3f7;
                border-radius: 4px;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #1e1e1e;
                width: 6px;
            }
            QScrollBar::handle:vertical {
                background: #444;
                border-radius: 3px;
            }
        """)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Titre
        title = QLabel("Receipt Reader")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet("color: #fff;")
        subtitle = QLabel("Extrait automatiquement le prix TTC, la TVA et l'adresse de tes tickets de caisse")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet("color: #666;")
        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # Drop zone
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        main_layout.addWidget(self.drop_zone)

        # Compteur fichiers sélectionnés
        self.file_count_label = QLabel("Aucun fichier sélectionné")
        self.file_count_label.setFont(QFont("Segoe UI", 10))
        self.file_count_label.setStyleSheet("color: #666;")
        main_layout.addWidget(self.file_count_label)

        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Status
        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet("color: #aaa;")
        main_layout.addWidget(self.status_label)

        # Boutons
        btn_layout = QHBoxLayout()
        self.btn_extract = QPushButton("⚙  Extraire les données")
        self.btn_extract.setEnabled(False)
        self.btn_extract.clicked.connect(self._start_extraction)

        self.btn_clear = QPushButton("Effacer")
        self.btn_clear.setObjectName("btn_secondary")
        self.btn_clear.setEnabled(False)
        self.btn_clear.clicked.connect(self._clear)

        btn_layout.addWidget(self.btn_extract)
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        # En-tête résultats
        header = QHBoxLayout()
        for text, width in [("Fichier", 200), ("Prix TTC", 90), ("TVA", 80), ("Adresse", None)]:
            lbl = QLabel(text)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #555; text-transform: uppercase;")
            if width:
                lbl.setFixedWidth(width)
            header.addWidget(lbl)
        main_layout.addLayout(header)

        # Zone résultats scrollable
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setSpacing(6)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.results_widget)
        main_layout.addWidget(scroll, stretch=1)

        # Bouton export CSV (caché au départ)
        self.btn_csv = QPushButton("⬇  Télécharger le CSV")
        self.btn_csv.setVisible(False)
        self.btn_csv.clicked.connect(self._open_csv)
        main_layout.addWidget(self.btn_csv)

        self.csv_path = None

    def _on_files_dropped(self, paths: list[str]):
        if not paths:
            # Clic sur la zone → ouvrir dialog
            paths, _ = QFileDialog.getOpenFileNames(
                self, "Sélectionner des tickets",
                "", "Images (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif)"
            )
        if paths:
            self.image_paths = list(set(self.image_paths + paths))
            self._update_file_count()

    def _update_file_count(self):
        n = len(self.image_paths)
        if n == 0:
            self.file_count_label.setText("Aucun fichier sélectionné")
            self.btn_extract.setEnabled(False)
            self.btn_clear.setEnabled(False)
        else:
            self.file_count_label.setText(f"{n} image(s) sélectionnée(s)")
            self.btn_extract.setEnabled(True)
            self.btn_clear.setEnabled(True)

    def _clear(self):
        self.image_paths = []
        self._update_file_count()
        self._clear_results()
        self.status_label.setText("")
        self.btn_csv.setVisible(False)
        self.csv_path = None

    def _clear_results(self):
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _start_extraction(self):
        if not self.image_paths:
            return

        self._clear_results()
        self.btn_extract.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.btn_csv.setVisible(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.image_paths))
        self.progress_bar.setValue(0)

        self.worker = OcrWorker(self.image_paths)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, index: int, filename: str):
        self.progress_bar.setValue(index + 1)
        self.status_label.setText(f"Traitement : {filename}...")

    def _on_finished(self, results: list, csv_path: str):
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"✅ {len(results)} ticket(s) traité(s)")
        self.btn_extract.setEnabled(True)
        self.btn_clear.setEnabled(True)
        self.csv_path = csv_path

        for data in results:
            row = ResultRow(data)
            self.results_layout.addWidget(row)

        self.btn_csv.setVisible(True)

    def _on_error(self, msg: str):
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"❌ Erreur : {msg}")
        self.btn_extract.setEnabled(True)
        self.btn_clear.setEnabled(True)

    def _open_csv(self):
        if self.csv_path and os.path.exists(self.csv_path):
            os.startfile(self.csv_path)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Receipt Reader")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
