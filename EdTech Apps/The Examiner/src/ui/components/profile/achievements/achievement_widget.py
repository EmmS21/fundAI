from PySide6.QtWidgets import QWidget, QHBoxLayout
from PySide6.QtCore import Qt
from .medal_widget import MedalWidget

class AchievementWidget(QWidget):
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self._setup_ui()
    
    def _setup_ui(self):
        # Create main layout
        main_layout = QHBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        self.setLayout(main_layout)
        
        # Create container widget with grey background
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border-radius: 16px;
                padding: 16px;
            }
        """)
        
        # Create layout for medals inside container
        medals_layout = QHBoxLayout()
        medals_layout.setSpacing(20)  # Space between medals
        medals_layout.setContentsMargins(20, 12, 20, 12)  # Padding inside container
        container.setLayout(medals_layout)
        
        # Add medals
        medals = self.user_data.medals or {'gold': 0, 'silver': 0, 'bronze': 0}
        for medal_type in ['gold', 'silver', 'bronze']:
            medal = MedalWidget(medal_type, medals.get(medal_type, 0))
            medals_layout.addWidget(medal)
        
        # Add container to main layout
        main_layout.addWidget(container)
