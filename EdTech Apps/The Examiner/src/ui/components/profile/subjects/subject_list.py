from PySide6.QtWidgets import QWidget, QVBoxLayout
from .subject_card import SubjectCard
from PySide6.QtCore import Signal

class SubjectList(QWidget):
    level_changed = Signal(str, dict)  # Forward level changes to parent
    subject_removed = Signal(str)  # Forward subject removal to parent
    
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
        self.layout.insertWidget(0, card)  # Add new subjects at the top
        card.show()
    
    def _on_subject_removed(self, subject_name):
        """Handle subject removal"""
        self.subject_removed.emit(subject_name)
        for i in range(self.layout.count()):
            widget = self.layout.itemAt(i).widget()
            if isinstance(widget, SubjectCard) and widget.subject_name == subject_name:
                widget.deleteLater()
                break
