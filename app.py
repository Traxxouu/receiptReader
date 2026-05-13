import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QScrollArea, QFrame, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from preprocessor import preprocess_image
from extractor import extract_text, parse_receipt
from validator import valider_adresse


# ─────────────────────────────────────────────
# Worker thread OCR
# ─────────────────────────────────────────────
class OcrWorker(QThread):
    progress = pyqtSignal(int, str)
    result_ready = pyqtSignal(dict)
    finished = pyqtSignal()

    def __init__(self, image_paths: list[str]):
        super().__init__()
        self.image_paths = image_paths

    def run(self):
        for i, img_path in enumerate(self.image_paths):
            filename = os.path.basename(img_path)
            self.progress.emit(i, filename)

            entry = {
                "fichier": filename,
                "numero_rue": None,
                "nom_rue": None,
                "code_postal": None,
                "ville": None,
                "adresse_validee": None,
                "confiance": None,
                "mode": None,
                "statut": "erreur",
            }

            try:
                img = preprocess_image(img_path)
                results = extract_text(img)
                data = parse_receipt(results)

                if not data["est_ticket"]:
                    entry["statut"] = "ignoré"
                    self.result_ready.emit(entry)
                    continue

                entry["numero_rue"] = data["numero_rue"]
                entry["nom_rue"] = data["nom_rue"]
                entry["code_postal"] = data["code_postal"]

                if data["numero_rue"] or data["nom_rue"] or data["code_postal"]:
                    validation = valider_adresse(
                        data["numero_rue"],
                        data["nom_rue"],
                        data["code_postal"]
                    )
                    entry["adresse_validee"] = validation["adresse_validee"]
                    entry["ville"] = validation["ville"]
                    entry["confiance"] = validation["confiance"]
                    entry["mode"] = validation["mode"]
                    entry["statut"] = "ok" if validation["adresse_validee"] else "partiel"
                else:
                    entry["statut"] = "non trouvé"

            except Exception as e:
                entry["statut"] = f"erreur: {str(e)[:40]}"

            self.result_ready.emit(entry)

        self.finished.emit()


# ─────────────────────────────────────────────
# Zone drag & drop
# ─────────────────────────────────────────────
class DropZone(QFrame):
    files_dropped = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_style(False)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("📂")
        icon.setFont(QFont("Segoe UI Emoji", 32))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel("Glisse tes tickets ici  ·  ou clique pour sélectionner")
        self.label.setFont(QFont("Segoe UI", 11))
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #888;")

        layout.addWidget(icon)
        layout.addWidget(self.label)

    def _set_style(self, hover: bool):
        color = "#4fc3f7" if hover else "#444"
        bg = "#1a2a35" if hover else "#1a1a1a"
        self.setStyleSheet(f"""
            DropZone {{
                border: 2px dashed {color};
                border-radius: 12px;
                background-color: {bg};
            }}
        """)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._set_style(True)

    def dragLeaveEvent(self, e):
        self._set_style(False)

    def dropEvent(self, e):
        self._set_style(False)
        exts = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif")
        paths = [u.toLocalFile() for u in e.mimeData().urls()
                 if u.toLocalFile().lower().endswith(exts)]
        if paths:
            self.files_dropped.emit(paths)

    def mousePressEvent(self, e):
        self.files_dropped.emit([])


# ─────────────────────────────────────────────
# Ligne de résultat
# ─────────────────────────────────────────────
class ResultRow(QFrame):
    STATUT_COLORS = {
        "ok": "#4fc3f7",
        "partiel": "#ffb74d",
        "ignoré": "#666",
        "non trouvé": "#ef5350",
        "erreur": "#ef5350",
    }

    def __init__(self, data: dict):
        super().__init__()
        self.setStyleSheet("ResultRow { background-color: #222; border-radius: 8px; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(16)

        statut = data.get("statut", "erreur")
        color = self.STATUT_COLORS.get(statut, "#666")

        # Indicateur statut
        dot = QLabel("●")
        dot.setFixedWidth(14)
        dot.setFont(QFont("Segoe UI", 10))
        dot.setStyleSheet(f"color: {color};")

        # Fichier
        fichier = QLabel(data.get("fichier", ""))
        fichier.setFixedWidth(210)
        fichier.setFont(QFont("Segoe UI", 9))
        fichier.setStyleSheet("color: #888;")

        # Rue
        rue = ""
        if data.get("numero_rue") and data.get("nom_rue"):
            rue = f"{data['numero_rue']} {data['nom_rue']}"
        elif data.get("nom_rue"):
            rue = data["nom_rue"]

        rue_lbl = QLabel(rue or "—")
        rue_lbl.setFixedWidth(200)
        rue_lbl.setFont(QFont("Segoe UI", 10))
        rue_lbl.setStyleSheet("color: #ccc;")

        # Code postal
        cp_lbl = QLabel(data.get("code_postal") or "—")
        cp_lbl.setFixedWidth(70)
        cp_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        cp_lbl.setStyleSheet("color: #4fc3f7;")

        # Ville déduite
        ville_lbl = QLabel(data.get("ville") or "—")
        ville_lbl.setFont(QFont("Segoe UI", 10))
        ville_lbl.setStyleSheet("color: #81c784;")

        layout.addWidget(dot)
        layout.addWidget(fichier)
        layout.addWidget(rue_lbl)
        layout.addWidget(cp_lbl)
        layout.addWidget(ville_lbl)
        layout.addStretch()


# ─────────────────────────────────────────────
# Fenêtre principale
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Receipt Reader")
        self.setMinimumSize(900, 640)
        self.image_paths = []
        self.worker = None
        self.all_results = []
        self._build_ui()
        self._apply_theme()

    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #111; color: #ddd; }
            QPushButton {
                background-color: #4fc3f7; color: #000;
                border: none; border-radius: 8px;
                padding: 10px 24px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background-color: #81d4fa; }
            QPushButton:disabled { background-color: #2a2a2a; color: #555; }
            QPushButton#secondary {
                background-color: #222; color: #888;
                border: 1px solid #333;
            }
            QPushButton#secondary:hover { background-color: #2a2a2a; color: #ccc; }
            QProgressBar {
                background-color: #222; border-radius: 4px;
                height: 6px; text-align: center; border: none;
            }
            QProgressBar::chunk { background-color: #4fc3f7; border-radius: 4px; }
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: #1a1a1a; width: 6px; }
            QScrollBar::handle:vertical { background: #444; border-radius: 3px; }
        """)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setContentsMargins(28, 28, 28, 28)
        main.setSpacing(14)

        # Titre
        title = QLabel("Receipt Reader")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet("color: #fff;")
        sub = QLabel("Extrait automatiquement l'adresse de tes tickets de caisse")
        sub.setFont(QFont("Segoe UI", 10))
        sub.setStyleSheet("color: #555;")
        main.addWidget(title)
        main.addWidget(sub)

        # Drop zone
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        main.addWidget(self.drop_zone)

        # Compteur + boutons
        row = QHBoxLayout()
        self.file_count = QLabel("Aucun fichier sélectionné")
        self.file_count.setStyleSheet("color: #555; font-size: 11px;")
        self.btn_extract = QPushButton("⚙  Extraire les adresses")
        self.btn_extract.setEnabled(False)
        self.btn_extract.clicked.connect(self._start)
        self.btn_clear = QPushButton("Effacer")
        self.btn_clear.setObjectName("secondary")
        self.btn_clear.setEnabled(False)
        self.btn_clear.clicked.connect(self._clear)
        row.addWidget(self.file_count)
        row.addStretch()
        row.addWidget(self.btn_clear)
        row.addWidget(self.btn_extract)
        main.addLayout(row)

        # Progress + status
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setTextVisible(False)
        self.status = QLabel("")
        self.status.setStyleSheet("color: #666; font-size: 11px;")
        main.addWidget(self.progress)
        main.addWidget(self.status)

        # En-tête colonnes
        header = QHBoxLayout()
        header.setContentsMargins(14, 0, 14, 0)
        header.setSpacing(16)
        for txt, w in [("", 14), ("Fichier", 210), ("Rue", 200), ("Code postal", 70), ("Ville déduite", None)]:
            lbl = QLabel(txt)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #444;")
            if w:
                lbl.setFixedWidth(w)
            header.addWidget(lbl)
        header.addStretch()
        main.addLayout(header)

        # Résultats
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setSpacing(6)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.results_widget)
        main.addWidget(scroll, stretch=1)

    def _on_files_dropped(self, paths):
        if not paths:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "Sélectionner des tickets", "",
                "Images (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif)"
            )
        if paths:
            self.image_paths = list(set(self.image_paths + paths))
            n = len(self.image_paths)
            self.file_count.setText(f"{n} image(s) sélectionnée(s)")
            self.btn_extract.setEnabled(True)
            self.btn_clear.setEnabled(True)

    def _clear(self):
        self.image_paths = []
        self.all_results = []
        self.file_count.setText("Aucun fichier sélectionné")
        self.btn_extract.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.status.setText("")
        self._clear_results()

    def _clear_results(self):
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _start(self):
        self._clear_results()
        self.all_results = []
        self.btn_extract.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(len(self.image_paths))
        self.progress.setValue(0)

        self.worker = OcrWorker(self.image_paths)
        self.worker.progress.connect(self._on_progress)
        self.worker.result_ready.connect(self._on_result)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, i, filename):
        self.progress.setValue(i + 1)
        self.status.setText(f"Traitement : {filename}...")

    def _on_result(self, data):
        self.all_results.append(data)
        row = ResultRow(data)
        self.results_layout.addWidget(row)

    def _on_finished(self):
        self.progress.setVisible(False)
        ok = sum(1 for r in self.all_results if r["statut"] == "ok")
        total = len(self.all_results)
        self.status.setText(f"✅ Terminé — {ok}/{total} adresses trouvées")
        self.btn_extract.setEnabled(True)
        self.btn_clear.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Receipt Reader")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
