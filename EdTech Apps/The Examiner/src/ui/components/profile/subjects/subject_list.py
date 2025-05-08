from PySide6.QtWidgets import QWidget, QVBoxLayout
from .subject_card import SubjectCard
from PySide6.QtCore import Signal, Slot
import logging

logger = logging.getLogger(__name__)

class SubjectList(QWidget):
    level_changed = Signal(str, dict)  # Forward level changes to parent
    subject_removed = Signal(str)  # Forward subject removal to parent
    test_requested = Signal(str, str)
    report_view_requested = Signal(int) 
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(12)  # Spacing between cards
        self.layout.setContentsMargins(0, 0, 0, 0)
        
    def add_subject(self, subject_name, levels=None):
        """Add a new subject card to the list"""
        card = SubjectCard(subject_name, levels)
        card.deleted.connect(self._on_subject_removed)
        card.levels_changed.connect(self.level_changed.emit)
        card.report_view_requested.connect(self.report_view_requested.emit) 

        try:
            logger.info(f"[SubjectList] Attempting connect for {subject_name}...")
            connection_successful = card.start_test_requested.connect(self.on_card_test_requested)
            logger.info(f"[SubjectList] Connection for {subject_name} successful: {connection_successful is not None}")

        except Exception as e:
             logger.error(f"[SubjectList] *** EXCEPTION during connect for {subject_name}: {e} ***", exc_info=True)

        self.layout.insertWidget(0, card)
        card.show()
    
    @Slot(str)
    def _on_subject_removed(self, subject_name):
        """Handle subject removal"""
        widget_to_remove = None
        for i in range(self.layout.count()):
            widget = self.layout.itemAt(i).widget()
            if isinstance(widget, SubjectCard) and widget.subject_name == subject_name:
                widget_to_remove = widget
                break

        if widget_to_remove:
             self.subject_removed.emit(subject_name)
             widget_to_remove.deleteLater()
             logger.info(f"[SubjectList] Removed card for {subject_name}")
        else:
             logger.warning(f"[SubjectList] Could not find card to remove for {subject_name}")

    @Slot(str, str)
    def on_card_test_requested(self, subject_name, level_key):
        """Relays the signal from SubjectCard upwards."""
        logger.info(f"[SubjectList] Received test request for {subject_name}/{level_key}, emitting signal.")
        self.test_requested.emit(subject_name, level_key)
