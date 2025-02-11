from PySide6.QtWidgets import QPushButton, QLineEdit, QCalendarWidget, QDialog, QVBoxLayout, QLabel, QWidget, QHBoxLayout, QSpinBox, QToolButton, QMenu, QCompleter, QTabWidget, QComboBox
from PySide6.QtCore import Qt, QPropertyAnimation, QPoint, Property, QEasingCurve, QRect, QDate, QSize, QEvent, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QPalette, QPixmap
from datetime import datetime
import os
from src.utils.constants import COUNTRIES

class AnimatedButton(QPushButton):
    def __init__(self, text, is_primary=True, direction="forward"):
        super().__init__(text)
        self.is_primary = is_primary
        self.direction = direction  # "forward" or "backward"
        self._arrow_position = 0
        self._circle_progress = 0
        self.is_animating = False
        self._enabled = True
        self._error_message = ""
        
        # Setup animations
        self.hover_animation = QPropertyAnimation(self, b"arrow_position")
        self.hover_animation.setDuration(200)
        
        self.click_animation = QPropertyAnimation(self, b"circle_progress")
        self.click_animation.setDuration(500)
        self.click_animation.setEasingCurve(QEasingCurve.InOutQuad)
        # Connect animation finished signal to reset state
        self.click_animation.finished.connect(self.reset_state)
        
        # Style
        self.setFixedSize(160, 48)
        self.setCursor(Qt.PointingHandCursor)
        
    def reset_state(self):
        """Reset button to original state after animation completes"""
        self.is_animating = False
        self._circle_progress = 0
        self._arrow_position = 0
        self.update()
        
    def get_arrow_position(self):
        return self._arrow_position
        
    def set_arrow_position(self, pos):
        self._arrow_position = pos
        self.update()
        
    def get_circle_progress(self):
        return self._circle_progress
        
    def set_circle_progress(self, progress):
        self._circle_progress = progress
        self.update()
        
    def setEnabled(self, enabled: bool):
        self._enabled = enabled
        self.update()
        
    def setErrorMessage(self, message: str):
        self._error_message = message
        self.update()
        
    arrow_position = Property(float, get_arrow_position, set_arrow_position)
    circle_progress = Property(float, get_circle_progress, set_circle_progress)
    
    def enterEvent(self, event):
        if not self.is_animating:
            self.hover_animation.setStartValue(0)
            # Reverse direction for back button
            value = -10 if self.direction == "backward" else 10
            self.hover_animation.setEndValue(value)
            self.hover_animation.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        if not self.is_animating:
            # Reverse direction for back button
            value = -10 if self.direction == "backward" else 10
            self.hover_animation.setStartValue(value)
            self.hover_animation.setEndValue(0)
            self.hover_animation.start()
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        if self._enabled and not self.is_animating:
            self.is_animating = True
            self.click_animation.setStartValue(0)
            self.click_animation.setEndValue(100)
            self.click_animation.start()
            super().mousePressEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        
        if not self._enabled:
            # Draw disabled state
            painter.fillRect(rect, QColor("#e0e0e0"))
            painter.setPen(QColor("#999999"))
            text_rect = rect.adjusted(0, 0, -40, 0) if self.direction == "forward" else rect.adjusted(40, 0, 0, 0)
            painter.drawText(text_rect, Qt.AlignCenter, self.text())
            
            # Draw error message if exists
            if self._error_message:
                error_rect = QRect(rect.left(), rect.bottom() + 5, rect.width(), 20)
                painter.setPen(QColor("#ff4444"))
                painter.drawText(error_rect, Qt.AlignCenter, self._error_message)
            return
            
        if self.is_animating:
            # Draw circular progress
            pen = QPen(QColor("#4285f4"), 2)
            painter.setPen(pen)
            size = min(rect.width(), rect.height()) - 4
            x = (rect.width() - size) / 2
            y = (rect.height() - size) / 2
            painter.drawArc(int(x), int(y), size, size, 0, int(self._circle_progress * 360 * 16))
            
            # Draw arrow
            if self._circle_progress > 0.5:
                if self.direction == "backward":
                    # Draw left-pointing arrow
                    painter.drawLine(
                        rect.center().x() + 10,
                        rect.center().y(),
                        rect.center().x() - 10,
                        rect.center().y()
                    )
                    painter.drawLine(
                        rect.center().x() - 5,
                        rect.center().y() - 5,
                        rect.center().x() - 10,
                        rect.center().y()
                    )
                    painter.drawLine(
                        rect.center().x() - 5,
                        rect.center().y() + 5,
                        rect.center().x() - 10,
                        rect.center().y()
                    )
                else:
                    # Draw right-pointing arrow
                    painter.drawLine(
                        rect.center().x() - 10,
                        rect.center().y(),
                        rect.center().x() + 10,
                        rect.center().y()
                    )
                    painter.drawLine(
                        rect.center().x() + 5,
                        rect.center().y() - 5,
                        rect.center().x() + 10,
                        rect.center().y()
                    )
                    painter.drawLine(
                        rect.center().x() + 5,
                        rect.center().y() + 5,
                        rect.center().x() + 10,
                        rect.center().y()
                    )
        else:
            # Normal button state
            if self.is_primary:
                painter.fillRect(rect, QColor("#4285f4"))
            
            painter.setPen(QColor("white" if self.is_primary else "#666666"))
            
            # Adjust text position based on direction
            if self.direction == "backward":
                text_rect = rect.adjusted(40, 0, 0, 0)
            else:
                text_rect = rect.adjusted(0, 0, -40, 0)
            painter.drawText(text_rect, Qt.AlignCenter, self.text())
            
            # Draw arrow based on direction
            if self.direction == "backward":
                # Draw left-pointing arrow
                arrow_x = rect.left() + 30 + self._arrow_position
                painter.drawLine(
                    arrow_x + 10,
                    rect.center().y(),
                    arrow_x - 10,
                    rect.center().y()
                )
                painter.drawLine(
                    arrow_x - 5,
                    rect.center().y() - 5,
                    arrow_x - 10,
                    rect.center().y()
                )
                painter.drawLine(
                    arrow_x - 5,
                    rect.center().y() + 5,
                    arrow_x - 10,
                    rect.center().y()
                )
            else:
                # Draw right-pointing arrow
                arrow_x = rect.right() - 30 + self._arrow_position
                painter.drawLine(
                    arrow_x - 10,
                    rect.center().y(),
                    arrow_x + 10,
                    rect.center().y()
                )
                painter.drawLine(
                    arrow_x + 5,
                    rect.center().y() - 5,
                    arrow_x + 10,
                    rect.center().y()
                )
                painter.drawLine(
                    arrow_x + 5,
                    rect.center().y() + 5,
                    arrow_x + 10,
                    rect.center().y()
                )

class StyledButton(QPushButton):
    def __init__(self, text, is_primary=True):
        super().__init__(text)
        self.setStyleSheet("""
            QPushButton {
                background-color: """ + ("#4285f4" if is_primary else "transparent") + """;
                color: """ + ("white" if is_primary else "#666666") + """;
                border: none;
                border-radius: 24px;
                padding: 12px 32px;
                font-size: 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: """ + ("#357abd" if is_primary else "#f0f0f0") + """;
            }
        """)

class StyledInput(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QLineEdit {
                padding: 12px 16px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-size: 16px;
                background-color: white;
                color: #1a1a1a;
                min-width: 400px;
            }
            QLineEdit:focus {
                border: 2px solid #4285f4;
                padding: 11px 15px;
            }
            QLineEdit::placeholder {
                color: #999999;
            }
        """)

class YearMenu(QMenu):
    def event(self, event):
        if event.type() == QEvent.Show:
            # Move menu down by adding a vertical offset
            pos = self.parent().mapToGlobal(QPoint(0, self.parent().height()))
            self.move(pos)
        return super().event(event)

class CustomCalendarWidget(QCalendarWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(QSize(400, 400))
        
        # Set the minimum and maximum dates
        min_date = QDate(1950, 1, 1)
        max_date = QDate.currentDate()
        self.setDateRange(min_date, max_date)
        
        # Find the year button and set up its menu
        year_button = self.findChild(QToolButton, "qt_calendar_yearbutton")
        if year_button:
            menu = YearMenu(year_button)  # Use our custom menu
            for year in range(max_date.year(), 1949, -1):
                action = menu.addAction(str(year))
                action.triggered.connect(lambda checked, y=year: self.setSelectedYear(y))
            year_button.setMenu(menu)
            year_button.setPopupMode(QToolButton.InstantPopup)
        
        self.setStyleSheet("""
            /* Main calendar widget */
            QCalendarWidget {
                background-color: white;
                color: black;
            }
            
            /* Month and Year buttons */
            QCalendarWidget QToolButton#qt_calendar_monthbutton,
            QCalendarWidget QToolButton#qt_calendar_yearbutton {
                color: black;
                background-color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 4px;
            }
            
            /* Remove dropdown arrows */
            QCalendarWidget QToolButton#qt_calendar_monthbutton::menu-indicator,
            QCalendarWidget QToolButton#qt_calendar_yearbutton::menu-indicator {
                image: none;
            }
            
            /* Selection menu */
            QCalendarWidget QMenu {
                background-color: white;
            }
            QCalendarWidget QMenu::item {
                color: black;
                padding: 6px 24px;
            }
            QCalendarWidget QMenu::item:selected {
                background-color: #1a73e8;
                color: white;
            }
            
            /* Days grid */
            QCalendarWidget QAbstractItemView {
                background-color: white;
                color: black;
                selection-background-color: #1a73e8;
                selection-color: white;
                font-size: 16px;
            }
            
            /* Individual day cells */
            QCalendarWidget QAbstractItemView::item {
                color: black;
                border: none;
                padding: 6px;
            }
            
            /* Selected date */
            QCalendarWidget QAbstractItemView::item:selected {
                background-color: #1a73e8;
                color: white;
                border-radius: 4px;
            }
            
            /* Header (S M T W T F S) */
            QCalendarWidget QHeaderView::section {
                background-color: white;
                color: black;
                font-size: 14px;
                font-weight: bold;
                padding: 6px;
                border: none;
            }
            
            /* Navigation bar */
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: white;
            }
            
            /* Weekend days */
            QCalendarWidget QAbstractItemView::item[weekendDay="true"] {
                color: #FF0000;
            }
            
            /* Disabled dates */
            QCalendarWidget QAbstractItemView::item:disabled {
                color: #cccccc;
            }

            /* Just hide the spinbox without affecting layout */
            QCalendarWidget QSpinBox#qt_calendar_yearedit {
                background: transparent;
                border: none;
                color: transparent;
            }
        """)
        
        # Create and set a small down arrow icon programmatically
        self.create_down_arrow_icon()
        
        # Remove grid lines
        self.setGridVisible(False)
        
        # Set header format
        self.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.SingleLetterDayNames)
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        
        # Set selection mode
        self.setSelectionMode(QCalendarWidget.SelectionMode.SingleSelection)
        
    def create_down_arrow_icon(self):
        """Create a small down arrow icon and save it as a temporary file"""
        # Create a small pixmap for the arrow
        pixmap = QPixmap(12, 12)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background
        
        # Draw the arrow
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor('black'), 1))
        
        # Draw arrow pointing down
        painter.drawLine(3, 4, 6, 7)
        painter.drawLine(6, 7, 9, 4)
        
        painter.end()
        
        # Save the arrow icon temporarily
        temp_path = os.path.join(os.path.dirname(__file__), 'down_arrow.png')
        pixmap.save(temp_path)

    def setSelectedYear(self, year):
        current_date = self.selectedDate()
        new_date = QDate(year, current_date.month(), current_date.day())
        self.setSelectedDate(new_date)

class DateInput(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setPlaceholderText("Select your birth date")
        self.setCursor(Qt.PointingHandCursor)
        
        # Style the input field
        self.setStyleSheet("""
            QLineEdit {
                background-color: white;
                padding: 12px 16px;
                border: 1px solid #ddd;
                border-radius: 12px;
                font-size: 16px;
                color: #1a1a1a;
                min-height: 24px;
            }
            QLineEdit:focus {
                border: 2px solid #4285f4;
            }
            QLineEdit::placeholder {
                color: #999999;
            }
        """)
        
        # Calendar dialog setup
        self.calendar_dialog = QDialog()
        self.calendar_dialog.setWindowTitle("Select Birth Date")
        self.calendar_dialog.setFixedSize(500, 600)  # Larger fixed size
        self.calendar_dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 20px;
            }
        """)
        
        # Dialog layout
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Header
        header = QLabel("Select Birth Date")
        header.setStyleSheet("""
            QLabel {
                color: #1a1a1a;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        layout.addWidget(header)
        
        # Calendar
        self.calendar = CustomCalendarWidget()
        self.calendar.setMaximumDate(QDate.currentDate())
        layout.addWidget(self.calendar)
        
        # Button container
        button_container = QWidget()
        button_layout = QHBoxLayout()
        button_container.setLayout(button_layout)
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #666666;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        cancel_btn.clicked.connect(self.calendar_dialog.reject)
        
        # Select button
        select_btn = QPushButton("Select")
        select_btn.setStyleSheet("""
            QPushButton {
                background-color: #4285f4;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        select_btn.clicked.connect(lambda: self.date_selected(self.calendar.selectedDate()))
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(select_btn)
        layout.addWidget(button_container)
        
        self.calendar_dialog.setLayout(layout)
        
        # Connect signals
        self.calendar.clicked.connect(self.date_selected)
        self.clicked = self.mousePressEvent
        
    def mousePressEvent(self, event):
        self.calendar_dialog.exec()
        
    def date_selected(self, qdate):
        self.setText(qdate.toString("MMMM d, yyyy"))
        self.calendar_dialog.accept()
        
    def get_date(self):
        try:
            return datetime.strptime(self.text(), "%B %d, %Y").date()
        except ValueError:
            return None

class CountryInput(StyledInput):
    def __init__(self):
        super().__init__()
        # Create completer with country list
        completer = QCompleter(COUNTRIES)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionMode(QCompleter.InlineCompletion)  # Set inline completion
        self.setCompleter(completer)

class SchoolLevelInput(QWidget):
    textChanged = Signal(str)
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create and style tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { 
                border: none;
            }
            QTabBar::tab {
                background: white;
                border: none;
                padding: 8px 16px;
                margin-right: 4px;
                border-radius: 8px;
                color: black;
            }
            QTabBar::tab:selected {
                background: #4285f4;
                color: white;
            }
            QTabBar::tab:!selected {
                background: white;
                border: 1px solid #e0e0e0;
            }
            QTabBar::tab:hover:!selected {
                background: #f5f5f5;
            }
        """)
        layout.addWidget(self.tabs)
        
        # Primary School tab
        primary_tab = QWidget()
        primary_layout = QVBoxLayout()
        primary_tab.setLayout(primary_layout)
        
        self.primary_grade = QComboBox()
        self.primary_grade.addItems([f"Grade {i}" for i in range(1, 8)])
        self.primary_grade.setStyleSheet("""
            QComboBox {
                color: black;
            }
        """)
        self.primary_grade.currentTextChanged.connect(self._on_value_changed)
        primary_layout.addWidget(self.primary_grade)
        
        # High School tab
        high_school_tab = QWidget()
        high_school_layout = QVBoxLayout()
        high_school_tab.setLayout(high_school_layout)
        
        self.high_school_form = QComboBox()
        self.high_school_form.addItems([f"Form {i}" for i in range(1, 7)])
        self.high_school_form.setStyleSheet("""
            QComboBox {
                color: black;
            }
        """)
        self.high_school_form.currentTextChanged.connect(self._on_value_changed)
        high_school_layout.addWidget(self.high_school_form)
        
        # Add tabs
        self.tabs.addTab(primary_tab, "Primary School")
        self.tabs.addTab(high_school_tab, "High School")
        self.tabs.currentChanged.connect(self._on_value_changed)
    
    def _on_value_changed(self):
        # Emit current selection when anything changes
        if self.tabs.currentIndex() == 0:
            value = f"Primary: {self.primary_grade.currentText()}"
        else:
            value = f"High School: {self.high_school_form.currentText()}"
        self.textChanged.emit(value)

    def text(self):
        # Return current selection based on active tab
        if self.tabs.currentIndex() == 0:
            return f"Primary: {self.primary_grade.currentText()}"
        else:
            return f"High School: {self.high_school_form.currentText()}"
