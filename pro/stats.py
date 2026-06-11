# pro/stats.py
import datetime
import csv
import os
import json
import threading
from collections import defaultdict
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QApplication, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QRectF, QTimer
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QLinearGradient, QBrush, QPen, QFont
from auth import get_supabase_client
from .dashboard import generate_dashboard
from .gate import CurrencyWorker

# ── Design tokens (matching app.py) ──────────────────
BG_0      = "#0f0d0e"
BG_1      = "#171415"
ACCENT     = "#FB7185"
ACCENT_2   = "#A78BFA"
ACCENT_DIM = "rgba(251, 113, 133, 45)"
ACCENT_BDR = "rgba(251, 113, 133, 100)"
TEXT_HI    = "rgba(255,255,255,255)"
TEXT_MID   = "rgba(255,255,255,190)"
TEXT_LOW   = "rgba(255,255,255,120)"
BORDER     = "rgba(251, 113, 133, 40)"

class PromoAdCard(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedHeight(150)
        
        self._build_ui()
        
        # Start currency worker thread
        self.currency_worker = CurrencyWorker(1080)
        self.currency_thread = threading.Thread(target=self.currency_worker.run, daemon=True)
        self.currency_worker.finished.connect(self._on_currency_resolved)
        self.currency_thread.start()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)
        
        # Header layout
        hl = QHBoxLayout()
        icon = QLabel("✦")
        icon.setStyleSheet(f"color: {ACCENT}; font-size: 14px; font-weight: bold; background: transparent;")
        title = QLabel("unlock pro tier")
        title.setFont(QFont("DM Mono", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: white; background: transparent;")
        hl.addWidget(icon)
        hl.addWidget(title)
        hl.addStretch()
        
        self.price_lbl = QLabel("₹1,080 lifetime")
        self.price_lbl.setFont(QFont("DM Mono", 10, QFont.Weight.Bold))
        self.price_lbl.setStyleSheet(f"color: {ACCENT}; background: transparent;")
        hl.addWidget(self.price_lbl)
        lay.addLayout(hl)
        
        # Description
        desc = QLabel("Get interactive dashboard, CSV export, custom rest screen messages, sounds, and GIF packs.")
        desc.setWordWrap(True)
        desc.setFont(QFont("DM Sans", 9))
        desc.setStyleSheet(f"color: {TEXT_MID}; background: transparent; line-height: 1.3;")
        lay.addWidget(desc)
        
        lay.addStretch()
        
        # Call to Action button
        self.btn_action = QPushButton("get pro now")
        self.btn_action.setFixedHeight(30)
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 {ACCENT}, stop:1 {ACCENT_2});
                color: white;
                border: none;
                border-radius: 9px;
                font-size: 11px;
                font-family: 'DM Sans';
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #ff8da1, stop:1 #bfa3ff);
            }}
        """)
        self.btn_action.clicked.connect(self._open_upgrade)
        lay.addWidget(self.btn_action)

    def _on_currency_resolved(self, code, val, formatted_text):
        self.price_lbl.setText(f"{formatted_text} lifetime")

    def _open_upgrade(self):
        # Resolve main window reference (traverse upwards if needed)
        win = self.main_window
        if not win:
            # Fallback traversal
            parent = self.parent()
            while parent:
                if hasattr(parent, '_show_upgrade_dialog'):
                    win = parent
                    break
                parent = parent.parent()
        if win and hasattr(win, '_show_upgrade_dialog'):
            win._show_upgrade_dialog()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 12, 12)
        
        # Gorgeous glowing semi-transparent background
        bg = QLinearGradient(0, 0, self.width(), self.height())
        bg.setColorAt(0, QColor(251, 113, 133, 20))
        bg.setColorAt(1, QColor(167, 139, 250, 20))
        p.fillPath(path, QBrush(bg))
        
        # Border
        border_pen = QPen()
        border_pen.setWidthF(1.0)
        border_grad = QLinearGradient(0, 0, self.width(), self.height())
        border_grad.setColorAt(0.0, QColor(251, 113, 133, 80))
        border_grad.setColorAt(1.0, QColor(167, 139, 250, 40))
        border_pen.setBrush(QBrush(border_grad))
        p.setPen(border_pen)
        p.drawPath(path)
        p.end()

class StatsWindow(QWidget):
    def __init__(self, user_info: dict, is_pro: bool, active_elapsed_secs: int = 0, is_embedded: bool = False, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self._user_info = user_info
        self._is_pro    = is_pro
        self._active_elapsed_secs = active_elapsed_secs
        self._is_embedded = is_embedded
        if not is_embedded:
            self.setFixedSize(320, 420)
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
            
            # Soft premium drop shadow
            self.shadow = QGraphicsDropShadowEffect(self)
            self.shadow.setBlurRadius(35)
            self.shadow.setColor(QColor(0, 0, 0, 160))
            self.shadow.setOffset(0, 8)
            self.setGraphicsEffect(self.shadow)
            
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui()
        if is_pro:
            self._load_stats()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # Title bar
        if not self._is_embedded:
            tb = QHBoxLayout()
            title = QLabel("focus stats")
            title.setFont(QFont("DM Mono", 12))
            title.setStyleSheet(f"color: {TEXT_HI}; background: transparent;")
            tb.addWidget(title)
            tb.addStretch()
            close_btn = QPushButton("×")
            close_btn.setFixedSize(24, 24)
            close_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {TEXT_LOW}; border: none; font-size: 18px; }} "
                f"QPushButton:hover {{ color: {TEXT_HI}; }}")
            close_btn.clicked.connect(self.close)
            tb.addWidget(close_btn)
            root.addLayout(tb)

        # Stats Grid
        self.lbl_today  = self._add_stat_row(root, "Today", "-- min")
        self.lbl_week   = self._add_stat_row(root, "This week", "-- sessions")
        self.lbl_streak = self._add_stat_row(root, "Streak", "-- days")
        self.lbl_total  = self._add_stat_row(root, "Total focus", "-- hrs")

        # Category Breakdown Widget (Pro only)
        self.cat_widget = QWidget()
        self.cat_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.cat_lay = QVBoxLayout(self.cat_widget)
        self.cat_lay.setContentsMargins(0, 8, 0, 8)
        self.cat_lay.setSpacing(6)
        root.addWidget(self.cat_widget)

        root.addStretch()

        # Dashboard Button (Pro)
        self.btn_dashboard = QPushButton("◈ view interactive dashboard")
        self.btn_dashboard.setFixedHeight(36)
        self.btn_dashboard.setStyleSheet(f"""
            QPushButton {{ 
                background: {ACCENT_DIM}; 
                color: white; 
                border: 1px solid {ACCENT};
                border-radius: 10px; 
                padding: 6px; 
                font-size: 11px;
                font-family: 'DM Sans';
                font-weight: 500;
            }}
            QPushButton:hover {{ background: rgba(251, 113, 133, 75); }}
        """)
        self.btn_dashboard.clicked.connect(self._show_interactive_dashboard)
        root.addWidget(self.btn_dashboard)

        # Export Button (Pro)
        self.btn_export = QPushButton("↓ export csv")
        self.btn_export.setFixedHeight(36)
        self.btn_export.setStyleSheet(f"""
            QPushButton {{ 
                background: rgba(255,255,255,13); 
                color: {TEXT_MID}; 
                border: 1px solid {BORDER};
                border-radius: 10px; 
                padding: 6px; 
                font-size: 11px;
                font-family: 'DM Sans';
            }}
            QPushButton:hover {{ background: rgba(255,255,255,25); color: {TEXT_HI}; border-color: {ACCENT}; }}
        """)
        self.btn_export.clicked.connect(self._export_csv)
        root.addWidget(self.btn_export)

        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setFont(QFont("DM Mono", 10))
        self.status_lbl.setStyleSheet(f"color: {TEXT_LOW}; background: transparent;")
        root.addWidget(self.status_lbl)

        # Promo AD Card (Non-Pro replacement)
        self.promo_card = PromoAdCard(self.main_window, self)
        root.addWidget(self.promo_card)

        # Update initial pro visibility states
        self._update_pro_visibility()

    def _update_pro_visibility(self):
        is_pro = self._is_pro
        self.btn_dashboard.setVisible(is_pro)
        self.btn_export.setVisible(is_pro)
        self.status_lbl.setVisible(is_pro)
        self.promo_card.setVisible(not is_pro)
        self.cat_widget.setVisible(is_pro)

    def _add_stat_row(self, layout, label, value):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFont(QFont("DM Sans", 11))
        lbl.setStyleSheet(f"color: {TEXT_MID}; background: transparent;")
        val = QLabel(value)
        val.setFont(QFont("DM Mono", 11))
        val.setStyleSheet(f"color: {ACCENT}; background: transparent; font-weight: bold;")
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(val)
        layout.addLayout(row)
        return val

    def _load_stats(self):
        # Reset to 0 instead of --
        self.lbl_today.setText("0 min")
        self.lbl_week.setText("0 sess")
        self.lbl_total.setText("0 hrs")
        self.lbl_streak.setText("0 days")
        self._update_pro_visibility()

        if self._is_pro:
            self.status_lbl.setText("loading local stats...")

        try:
            # 1. Load from Local JSON (Primary)
            from assets import USER_DATA_DIR
            local_db = os.path.join(USER_DATA_DIR, "sessions.json")
            data = []
            if os.path.exists(local_db):
                with open(local_db, "r") as f:
                    data = json.load(f)
                print(f"[stats] loaded {len(data)} rows from local sessions.json")
            else:
                # 2. Fallback to Supabase
                print(f"[stats] local db not found at {local_db}, trying cloud...")
                sb = get_supabase_client()
                if sb:
                    sub = self._user_info.get("id")
                    if sub:
                        res = sb.table("sessions").select("*").eq("google_sub", sub).execute()
                        data = res.data
                        print(f"[stats] fetched {len(data) if data else 0} rows from cloud")

            if not data and self._active_elapsed_secs == 0: 
                if self._is_pro: self.status_lbl.setText("no sessions recorded yet")
                return

            # Use local time for stats comparison
            now_local = datetime.datetime.now()
            today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start  = today_start - datetime.timedelta(days=7)
            
            today_secs = self._active_elapsed_secs
            week_count = 1 if self._active_elapsed_secs > 0 else 0
            total_secs = self._active_elapsed_secs
            
            parsed_dates = set()
            if self._active_elapsed_secs > 0:
                parsed_dates.add(now_local.date())

            for r in data:
                try:
                    raw_ts = r.get("completed_at")
                    if not raw_ts: continue
                    
                    # Convert UTC from DB to local time
                    clean_ts = raw_ts.replace("Z", "+00:00")
                    utc_ts = datetime.datetime.fromisoformat(clean_ts)
                    local_ts = utc_ts.astimezone(None).replace(tzinfo=None) # naive local
                    
                    parsed_dates.add(local_ts.date())
                    
                    dur = r.get("duration_secs", 0)
                    total_secs += dur
                    if local_ts >= today_start:
                        today_secs += dur
                    if local_ts >= week_start:
                        week_count += 1
                except Exception as e:
                    print(f"[stats] row error: {e}")
                    continue

            self.lbl_today.setText(f"{today_secs // 60} min")
            self.lbl_week.setText(f"{week_count} sess")
            self.lbl_total.setText(f"{total_secs // 3600} hrs")
            
            # Streak logic
            days = sorted(list(parsed_dates), reverse=True)
            streak = 0
            today = datetime.date.today()
            yesterday = today - datetime.timedelta(days=1)
            
            if days:
                start_day = None
                if days[0] == today: start_day = today
                elif days[0] == yesterday: start_day = yesterday
                
                if start_day:
                    streak = 0
                    curr = start_day
                    for d in days:
                        if d == curr:
                            streak += 1
                            curr -= datetime.timedelta(days=1)
                        elif d > curr: continue # multiple sessions same day
                        else: break

            self.lbl_streak.setText(f"{streak} days")
            
            # --- Category Breakdown Calculation ---
            # Clear previous widgets in cat_lay
            while self.cat_lay.count() > 0:
                item = self.cat_lay.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()

            if self._is_pro:
                # Group work sessions by category
                cat_durations = defaultdict(int)
                total_work_secs = 0
                for r in data:
                    if r.get("phase") == "Work":
                        dur = r.get("duration_secs", 0)
                        raw_cat = r.get("category")
                        if raw_cat:
                            category = str(raw_cat).strip()
                        else:
                            # Try parsing from task bracket tag
                            task = r.get("task")
                            if task:
                                task_str = str(task).strip()
                                if task_str.startswith('[') and ']' in task_str:
                                    parsed_cat = task_str[1:task_str.index(']')]
                                    if parsed_cat in ["Coding", "Design", "Writing", "Research", "Learning", "Planning", "Other"]:
                                        category = parsed_cat
                                    else:
                                        category = "Uncategorized"
                                else:
                                    category = "Uncategorized"
                            else:
                                category = "Uncategorized"
                        cat_durations[category] += dur
                        total_work_secs += dur

                # Add active elapsed seconds to category mapping if active timer is running for Work phase
                if self._active_elapsed_secs > 0:
                    current_cat = "Coding"
                    if self.main_window and hasattr(self.main_window, 'task_category_combo'):
                        current_cat = self.main_window.task_category_combo.currentText()
                    cat_durations[current_cat] += self._active_elapsed_secs
                    total_work_secs += self._active_elapsed_secs

                if total_work_secs > 0:
                    # Title for Category Section
                    cat_header = QLabel("top categories")
                    cat_header.setFont(QFont("DM Mono", 10, QFont.Weight.Bold))
                    cat_header.setStyleSheet(f"color: {ACCENT_2}; background: transparent; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px;")
                    self.cat_lay.addWidget(cat_header)

                    from PyQt6.QtWidgets import QProgressBar
                    # Sort categories by duration descending
                    sorted_cats = sorted(cat_durations.items(), key=lambda x: x[1], reverse=True)
                    # Show up to top 3 categories
                    for cat_name, cat_secs in sorted_cats[:3]:
                        pct = (cat_secs / total_work_secs) * 100
                        cat_min = cat_secs // 60

                        # Label Row
                        row_w = QWidget()
                        row_w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                        row_w_lay = QHBoxLayout(row_w)
                        row_w_lay.setContentsMargins(0, 0, 0, 0)

                        lbl_name = QLabel(cat_name)
                        lbl_name.setFont(QFont("DM Sans", 10))
                        lbl_name.setStyleSheet(f"color: {TEXT_MID}; background: transparent;")
                        
                        lbl_val = QLabel(f"{cat_min}m ({int(pct)}%)")
                        lbl_val.setFont(QFont("DM Mono", 10))
                        lbl_val.setStyleSheet(f"color: {TEXT_LOW}; background: transparent;")
                        
                        row_w_lay.addWidget(lbl_name)
                        row_w_lay.addStretch()
                        row_w_lay.addWidget(lbl_val)
                        self.cat_lay.addWidget(row_w)

                        # Progress Bar
                        bar = QProgressBar()
                        bar.setRange(0, 100)
                        bar.setValue(int(pct))
                        bar.setTextVisible(False)
                        bar.setFixedHeight(5)
                        bar.setStyleSheet(f"""
                            QProgressBar {{
                                background: rgba(255, 255, 255, 13);
                                border: none;
                                border-radius: 2.5px;
                            }}
                            QProgressBar::chunk {{
                                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACCENT}, stop:1 {ACCENT_2});
                                border-radius: 2.5px;
                            }}
                        """)
                        self.cat_lay.addWidget(bar)

            if self._is_pro: self.status_lbl.setText(f"loaded {len(data)} local sessions")
            
        except Exception as e:
            print(f"[stats] load failed: {e}")
            if self._is_pro: self.status_lbl.setText(f"load error: {str(e)[:30]}")

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Sessions", f"goofyfocus_{datetime.date.today()}.csv", "CSV files (*.csv)")
        if not path: return
        self.btn_export.setText("exporting...")
        QApplication.processEvents()
        try:
            # 1. Load from Local JSON (Primary)
            from assets import USER_DATA_DIR
            local_db = os.path.join(USER_DATA_DIR, "sessions.json")
            rows = []
            if os.path.exists(local_db):
                with open(local_db, "r") as f:
                    rows = json.load(f)
            else:
                # 2. Fallback to Supabase
                sb = get_supabase_client()
                if sb:
                    sub = self._user_info.get("id")
                    if sub:
                        res = sb.table("sessions").select("completed_at, duration_secs, phase").eq("google_sub", sub).order("completed_at", desc=True).execute()
                        rows = res.data

            if rows:
                with open(path, 'w', newline='') as f:
                    # Filter keys to match CSV requirements
                    fieldnames = ["completed_at", "duration_secs", "phase"]
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    # Sort rows by completed_at descending (newest first)
                    rows.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
                    writer.writerows(rows)
                self.status_lbl.setText("✓ exported successfully")
            else:
                self.status_lbl.setText("no data to export")
            self.btn_export.setText("↓ export csv")
            QTimer.singleShot(3000, lambda: self.status_lbl.setText(""))
        except Exception as e:
            self.status_lbl.setText("export failed")
            self.btn_export.setText("↓ export csv")
            print(f"[stats] export failed: {e}")

    def _show_interactive_dashboard(self):
        self.btn_dashboard.setText("generating...")
        QApplication.processEvents()
        success = generate_dashboard(self._user_info)
        if success:
            self.status_lbl.setText("✓ dashboard opened in browser")
        else:
            self.status_lbl.setText("no data for dashboard")
        self.btn_dashboard.setText("◈ view interactive dashboard")
        QTimer.singleShot(3000, lambda: self.status_lbl.setText(""))

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos') and self._drag_pos:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e): self._drag_pos = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 16, 16)
        if self._is_embedded:
            # Nested glass style
            p.fillPath(path, QBrush(QColor(255, 255, 255, 10)))
            p.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
        else:
            # Floating dialog opaque gradient
            bg = QLinearGradient(0, 0, 0, self.height())
            bg.setColorAt(0, QColor("#1D1822"))
            bg.setColorAt(1, QColor("#110E14"))
            p.fillPath(path, QBrush(bg))
            
            # Glass double-highlight border
            border_grad = QLinearGradient(0, 0, self.width(), self.height())
            border_grad.setColorAt(0.0, QColor(255, 255, 255, 60))
            border_grad.setColorAt(1.0, QColor(255, 255, 255, 10))
            p.setPen(QPen(border_grad, 1.2))
        p.drawPath(path)
        p.end()
