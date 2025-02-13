from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

class ProfileInfoWidget(QWidget):
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self._setup_ui()
    
    def _setup_ui(self):
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 60, 20, 20)  # Top margin to account for profile picture overflow
        self.setLayout(layout)
        
        # Grid for info fields
        grid_layout = QGridLayout()
        grid_layout.setSpacing(16)
        
        def create_field(label_text, value):
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setSpacing(8)
            
            label = QLabel(label_text)
            label.setStyleSheet("""
                QLabel {
                    color: #1a1a1a;
                    font-size: 16px;
                    font-weight: bold;
                }
            """)
            
            value_label = QLabel(value)
            value_label.setStyleSheet("""
                QLabel {
                    background-color: white;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    padding: 12px;
                    font-size: 14px;
                    color: #374151;
                    min-width: 200px;
                }
            """)
            
            container_layout.addWidget(label)
            container_layout.addWidget(value_label)
            return container
        
        # Format Grade/Form display
        grade_text = f"{'Form' if self.user_data.school_level == 'high' else 'Grade'} {self.user_data.grade}"
        
        # Create fields
        fields = [
            ("School", "Not set"),
            ("Grade/Form", self.user_data.school_level.capitalize() if self.user_data.school_level else "Not set"),
            ("City", self.user_data.city or "Not set"),
            ("Country", self.user_data.country or "Not set")
        ]
        
        # Add fields to grid
        for i, (label, value) in enumerate(fields):
            row = i // 2
            col = i % 2
            grid_layout.addWidget(create_field(label, value), row, col)
        
        layout.addLayout(grid_layout) 