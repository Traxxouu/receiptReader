import sys
import os
import csv
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QScrollArea,
    QFrame, QProgressBar, QSizePolicy, QDialog, QInputDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QCursor, QPixmap

from preprocessor import preprocess_image
from extractor import extract_raw_text
from ia import extraire_adresse_ia
from distance import calculer_distance


# ─────────────────────────────────────────────
# Worker thread
# ─────────────────────────────────────────────
class Worker(QThread):
    progress = pyqtSignal(int, str)
    result_ready = pyqtSignal(dict)
    finished = pyqtSignal()

    def __init__(self, image_paths: list[str], adresse_labo: str):
        super().__init__()
        self.image_paths = image_paths
        self.adresse_labo = adresse_labo

    def run(self):
        for i, img_path in enumerate(self.image_paths):
            filename = os.path.basename(img_path)
            self.progress.emit(i, filename)

            entry = {
                "fichier": filename,
                "img_path": img_path,
                "adresse": "",
                "distance_km": "",
                "distance_raw": None,
                "statut": "erreur",
            }

            try:
                img = preprocess_image(img_path)
                texte = extract_raw_text(img)

                if not texte.strip():
                    entry["statut"] = "vide"
                    self.result_ready.emit(entry)
                    continue

                adresse = extraire_adresse_ia(texte)
                if adresse:
                    entry["adresse"] = adresse
                    dist = calculer_distance(self.adresse_labo, adresse)
                    entry["distance_raw"] = dist
                    entry["distance_km"] = f"{dist:.1f} km" if dist else "N/A"
                    entry["statut"] = "ok"
                else:
                    entry["statut"] = "non_trouve"

            except Exception as e:
                entry["statut"] = "erreur"
                entry["adresse"] = str(e)[:60]

            self.result_ready.emit(entry)

        self.finished.emit()


# ─────────────────────────────────────────────
# Fenetre apercu ticket
# ─────────────────────────────────────────────
class TicketViewer(QDialog):
    def __init__(self, img_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apercu du ticket")
        self.setMinimumSize(400, 600)
        self.setStyleSheet("background: #fff;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        img_label = QLabel()
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaledToWidth(500, Qt.TransformationMode.SmoothTransformation)
        img_label.setPixmap(pixmap)
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        scroll.setWidget(img_label)
        layout.addWidget(scroll)

        btn_close = QPushButton("Fermer")
        btn_close.setStyleSheet("""
            QPushButton {
                background: #1a1a1a; color: #fff;
                border: none; border-radius: 3px;
                padding: 10px; font-family: Georgia; font-size: 11px;
            }
            QPushButton:hover { background: #333; }
        """)
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)


# ─────────────────────────────────────────────
# Zone de drop
# ─────────────────────────────────────────────
class DropZone(QFrame):
    files_dropped = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._update_style(False)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)

        self.title = QLabel("Deposer les images ici")
        self.title.setFont(QFont("Georgia", 13))
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet("color: #999; letter-spacing: 1px;")

        self.sub = QLabel("ou cliquer pour selectionner")
        self.sub.setFont(QFont("Georgia", 9))
        self.sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub.setStyleSheet("color: #bbb; letter-spacing: 0.5px;")

        layout.addWidget(self.title)
        layout.addWidget(self.sub)

    def _update_style(self, active: bool):
        border = "#333" if not active else "#111"
        bg = "#fafafa" if not active else "#f0f0f0"
        self.setStyleSheet(f"""
            DropZone {{
                border: 1.5px dashed {border};
                border-radius: 4px;
                background: {bg};
            }}
        """)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._update_style(True)

    def dragLeaveEvent(self, e):
        self._update_style(False)

    def dropEvent(self, e):
        self._update_style(False)
        exts = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif")
        paths = [u.toLocalFile() for u in e.mimeData().urls()
                 if u.toLocalFile().lower().endswith(exts)]
        if paths:
            self.files_dropped.emit(paths)

    def mousePressEvent(self, e):
        self.files_dropped.emit([])


# ─────────────────────────────────────────────
# Ligne résultat
# ─────────────────────────────────────────────
class ResultRow(QFrame):
    adresse_modifiee = pyqtSignal(str, str)  # (fichier, nouvelle_adresse)

    STATUS_STYLE = {
        "ok": "#2d6a4f",
        "non_trouve": "#999",
        "vide": "#bbb",
        "erreur": "#c0392b",
    }

    def __init__(self, data: dict, adresse_labo: str):
        super().__init__()
        self.data = data
        self.adresse_labo = adresse_labo
        self.setStyleSheet("ResultRow { background: transparent; border-bottom: 1px solid #ececec; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(12)

        statut = data.get("statut", "erreur")
        color = self.STATUS_STYLE.get(statut, "#999")

        # Fichier
        fichier = QLabel(data.get("fichier", ""))
        fichier.setFixedWidth(190)
        fichier.setFont(QFont("Georgia", 9))
        fichier.setStyleSheet("color: #999;")

        # Adresse (editable au clic)
        self.adresse_lbl = QLabel(data.get("adresse") or "—")
        self.adresse_lbl.setFont(QFont("Georgia", 10))
        self.adresse_lbl.setStyleSheet(f"color: {color};")
        self.adresse_lbl.setWordWrap(True)
        self.adresse_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # Distance
        self.dist_lbl = QLabel(data.get("distance_km") or "—")
        self.dist_lbl.setFixedWidth(70)
        self.dist_lbl.setFont(QFont("Georgia", 10))
        self.dist_lbl.setStyleSheet("color: #555;")
        self.dist_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Bouton voir ticket
        btn_voir = QPushButton("Voir")
        btn_voir.setFixedWidth(44)
        btn_voir.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_voir.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #aaa;
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 4px 6px;
                font-family: Georgia;
                font-size: 10px;
            }
            QPushButton:hover { color: #1a1a1a; border-color: #999; }
        """)
        btn_voir.clicked.connect(self._voir_ticket)

        # Bouton corriger adresse
        btn_edit = QPushButton("Corriger")
        btn_edit.setFixedWidth(60)
        btn_edit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_edit.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #aaa;
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 4px 6px;
                font-family: Georgia;
                font-size: 10px;
            }
            QPushButton:hover { color: #1a1a1a; border-color: #999; }
        """)
        btn_edit.clicked.connect(self._corriger_adresse)

        layout.addWidget(fichier)
        layout.addWidget(self.adresse_lbl)
        layout.addWidget(self.dist_lbl)
        layout.addWidget(btn_voir)
        layout.addWidget(btn_edit)

    def _voir_ticket(self):
        img_path = self.data.get("img_path", "")
        if img_path and os.path.exists(img_path):
            viewer = TicketViewer(img_path, self)
            viewer.exec()

    def _corriger_adresse(self):
        adresse_actuelle = self.data.get("adresse", "")
        nouvelle, ok = QInputDialog.getText(
            self, "Corriger l'adresse",
            "Adresse corrigee :",
            text=adresse_actuelle
        )
        if ok and nouvelle.strip():
            nouvelle = nouvelle.strip()
            self.data["adresse"] = nouvelle
            self.adresse_lbl.setText(nouvelle)
            self.adresse_lbl.setStyleSheet("color: #1a5276;")  # bleu = corrige manuellement

            # Recalculer la distance
            dist = calculer_distance(self.adresse_labo, nouvelle)
            self.data["distance_raw"] = dist
            self.data["distance_km"] = f"{dist:.1f} km" if dist else "N/A"
            self.dist_lbl.setText(self.data["distance_km"])
            self.adresse_modifiee.emit(self.data["fichier"], nouvelle)


# ─────────────────────────────────────────────
# Fenetre principale
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Receipt Reader")
        self.setMinimumSize(1050, 700)
        self.image_paths = []
        self.all_results = []
        self.result_rows = []
        self.worker = None
        self.adresse_labo = ""
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #ffffff; color: #1a1a1a; }
            QLineEdit {
                border: none; border-bottom: 1.5px solid #ddd;
                padding: 8px 0; font-family: Georgia; font-size: 13px;
                color: #1a1a1a; background: transparent;
            }
            QLineEdit:focus { border-bottom: 1.5px solid #1a1a1a; }
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: #fff; width: 4px; border: none; }
            QScrollBar::handle:vertical { background: #ddd; border-radius: 2px; }
            QProgressBar {
                border: none; background: #f0f0f0;
                height: 2px; border-radius: 1px;
            }
            QProgressBar::chunk { background: #1a1a1a; border-radius: 1px; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Panneau gauche
        left = QWidget()
        left.setFixedWidth(280)
        left.setStyleSheet("background: #f7f7f7; border-right: 1px solid #e8e8e8;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(28, 36, 28, 36)
        ll.setSpacing(0)

        brand = QLabel("Receipt\nReader")
        brand.setFont(QFont("Georgia", 20))
        brand.setStyleSheet("color: #1a1a1a;")
        ll.addWidget(brand)

        ll.addSpacing(6)
        tagline = QLabel("Extraction automatique\nd'adresses de tickets")
        tagline.setFont(QFont("Georgia", 9))
        tagline.setStyleSheet("color: #999;")
        ll.addWidget(tagline)

        ll.addSpacing(40)

        lbl = QLabel("ADRESSE DU LABORATOIRE")
        lbl.setFont(QFont("Georgia", 8))
        lbl.setStyleSheet("color: #aaa; letter-spacing: 1.5px;")
        ll.addWidget(lbl)
        ll.addSpacing(8)

        self.labo_input = QLineEdit()
        self.labo_input.setPlaceholderText("ex: 15 rue de la Paix, 75001 Paris")
        ll.addWidget(self.labo_input)

        ll.addSpacing(40)

        self.btn_extract = QPushButton("Extraire les adresses")
        self.btn_extract.setEnabled(False)
        self.btn_extract.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_extract.setStyleSheet("""
            QPushButton {
                background: #1a1a1a; color: #fff; border: none;
                border-radius: 3px; padding: 13px 20px;
                font-family: Georgia; font-size: 12px; letter-spacing: 0.5px;
            }
            QPushButton:hover { background: #333; }
            QPushButton:disabled { background: #e0e0e0; color: #aaa; }
        """)
        self.btn_extract.clicked.connect(self._start)
        ll.addWidget(self.btn_extract)

        ll.addSpacing(10)

        self.btn_xlsx = QPushButton("Exporter en Excel (.xlsx)")
        self.btn_xlsx.setVisible(False)
        self.btn_xlsx.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_xlsx.setStyleSheet("""
            QPushButton {
                background: transparent; color: #1a1a1a;
                border: 1.5px solid #1a1a1a; border-radius: 3px;
                padding: 11px 20px; font-family: Georgia;
                font-size: 12px; letter-spacing: 0.5px;
            }
            QPushButton:hover { background: #f0f0f0; }
        """)
        self.btn_xlsx.clicked.connect(self._export_xlsx)
        ll.addWidget(self.btn_xlsx)

        ll.addSpacing(10)

        self.btn_clear = QPushButton("Effacer")
        self.btn_clear.setVisible(False)
        self.btn_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background: transparent; color: #999; border: none;
                padding: 8px 0; font-family: Georgia; font-size: 11px; text-align: left;
            }
            QPushButton:hover { color: #1a1a1a; }
        """)
        self.btn_clear.clicked.connect(self._clear)
        ll.addWidget(self.btn_clear)

        ll.addStretch()

        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Georgia", 9))
        self.status_label.setStyleSheet("color: #aaa;")
        self.status_label.setWordWrap(True)
        ll.addWidget(self.status_label)

        root.addWidget(left)

        # ── Panneau droit
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(40, 36, 40, 36)
        rl.setSpacing(0)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(2)
        rl.addWidget(self.progress)
        rl.addSpacing(28)

        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        rl.addWidget(self.drop_zone)

        rl.addSpacing(28)

        self.section_label = QLabel("FICHIERS SELECTIONNES")
        self.section_label.setFont(QFont("Georgia", 8))
        self.section_label.setStyleSheet("color: #aaa; letter-spacing: 1.5px;")
        self.section_label.setVisible(False)
        rl.addWidget(self.section_label)

        rl.addSpacing(8)

        # En-tetes colonnes
        self.col_header = QWidget()
        ch = QHBoxLayout(self.col_header)
        ch.setContentsMargins(0, 0, 0, 0)
        ch.setSpacing(12)
        for txt, w in [("FICHIER", 190), ("ADRESSE EXTRAITE", None), ("DISTANCE", 70), ("", 44), ("", 60)]:
            lbl2 = QLabel(txt)
            lbl2.setFont(QFont("Georgia", 8))
            lbl2.setStyleSheet("color: #ccc; letter-spacing: 1px;")
            if w:
                lbl2.setFixedWidth(w)
            else:
                lbl2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            ch.addWidget(lbl2)
        self.col_header.setVisible(False)
        rl.addWidget(self.col_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(0)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.content_widget)
        rl.addWidget(scroll, stretch=1)

        root.addWidget(right, stretch=1)

    def _on_files_dropped(self, paths):
        if not paths:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "Selectionner des tickets", "",
                "Images (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif)"
            )
        if paths:
            self.image_paths = list(set(self.image_paths + paths))
            self._refresh_file_list()

    def _refresh_file_list(self):
        self._clear_content()
        self.section_label.setText(f"FICHIERS SELECTIONNES  —  {len(self.image_paths)} image(s)")
        self.section_label.setVisible(True)
        self.col_header.setVisible(False)
        self.btn_extract.setEnabled(True)
        self.btn_clear.setVisible(True)
        self.status_label.setText("")

    def _clear_content(self):
        self.result_rows = []
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _clear(self):
        self.image_paths = []
        self.all_results = []
        self._clear_content()
        self.section_label.setVisible(False)
        self.col_header.setVisible(False)
        self.btn_extract.setEnabled(False)
        self.btn_clear.setVisible(False)
        self.btn_xlsx.setVisible(False)
        self.status_label.setText("")
        self.progress.setVisible(False)

    def _start(self):
        self.adresse_labo = self.labo_input.text().strip()
        if not self.adresse_labo:
            self.status_label.setText("Veuillez saisir l'adresse du laboratoire.")
            return

        self._clear_content()
        self.all_results = []
        self.btn_extract.setEnabled(False)
        self.btn_xlsx.setVisible(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(len(self.image_paths))
        self.progress.setValue(0)

        self.section_label.setText("RESULTATS")
        self.section_label.setVisible(True)
        self.col_header.setVisible(True)

        self.worker = Worker(self.image_paths, self.adresse_labo)
        self.worker.progress.connect(self._on_progress)
        self.worker.result_ready.connect(self._on_result)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, i, filename):
        self.progress.setValue(i + 1)
        self.status_label.setText(f"Traitement : {filename}")

    def _on_result(self, data):
        self.all_results.append(data)
        row = ResultRow(data, self.adresse_labo)
        self.result_rows.append(row)
        self.content_layout.addWidget(row)

    def _on_finished(self):
        self.progress.setVisible(False)
        ok = sum(1 for r in self.all_results if r["statut"] == "ok")
        self.status_label.setText(f"{ok}/{len(self.all_results)} adresses trouvees")
        self.btn_extract.setEnabled(True)
        self.btn_xlsx.setVisible(True)

    def _export_xlsx(self):
        if not self.all_results:
            return

        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            self.status_label.setText("Installation de openpyxl en cours...")
            import subprocess
            subprocess.run([sys.executable, "-m", "pip", "install", "openpyxl"], capture_output=True)
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter en Excel",
            f"notes_de_frais_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel (*.xlsx)"
        )
        if not path:
            return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Notes de frais"

        # En-têtes — colonnes exactes du tableau du maitre de stage
        headers = [
            "Adresse de depart",
            "Adresse d'arrivee",
            "Nom du commerce (fichier)",
            "Distance",
            "A/R?",
            "Date",
        ]

        header_font = Font(bold=True, name="Calibri", size=11)
        header_fill = PatternFill("solid", fgColor="F2F2F2")
        thin = Side(style="thin", color="DDDDDD")
        border = Border(bottom=thin)

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="left", vertical="center")
            cell.border = border

        # Données
        today = datetime.now().strftime("%d/%m/%Y")
        for row_data in self.all_results:
            adresse = row_data.get("adresse", "")
            dist_raw = row_data.get("distance_raw")
            dist_str = f"{dist_raw:.1f}" if dist_raw else ""

            row_values = [
                self.adresse_labo,          # Adresse de depart
                adresse,                     # Adresse d'arrivee
                row_data.get("fichier", ""), # Nom du commerce
                dist_str,                    # Distance (nombre seul pour Excel)
                "x",                         # A/R? (comme dans le tableau)
                today,                       # Date
            ]
            ws.append(row_values)

        # Largeurs colonnes
        col_widths = [35, 40, 30, 12, 8, 14]
        for i, width in enumerate(col_widths, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width

        # Style lignes données
        data_font = Font(name="Calibri", size=10)
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
            for cell in row:
                cell.font = data_font
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.border = Border(bottom=Side(style="thin", color="F0F0F0"))

        ws.row_dimensions[1].height = 22
        ws.freeze_panes = "A2"

        wb.save(path)
        self.status_label.setText("Fichier Excel sauvegarde.")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Receipt Reader")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
