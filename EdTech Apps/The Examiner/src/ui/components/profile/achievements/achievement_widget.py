from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from .medal_widget import MedalWidget

class AchievementWidget(QWidget):
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self._setup_ui()
    
    def _setup_ui(self):
        # Create main layout
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        self.setLayout(main_layout)
        
        # Create container widget with grey background
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        
        # Create layout for medals inside container
        medals_layout = QHBoxLayout()
        medals_layout.setSpacing(5)
        medals_layout.setContentsMargins(20, 12, 20, 12)
        container.setLayout(medals_layout)
        
        # Add medals with their percentage labels
        medals = self.user_data.medals or {'gold': 0, 'silver': 0, 'bronze': 0}
        for medal_type in ['gold', 'silver', 'bronze']:
            # Create vertical layout for each medal group
            medal_group = QVBoxLayout()
            medal_group.setAlignment(Qt.AlignCenter)
            
            # Add medal
            medal = MedalWidget(medal_type, medals.get(medal_type, 0))
            medal_group.addWidget(medal)
            
            # Add percentage label
            percentage_label = QLabel(self._get_percentage_text(medal_type))
            percentage_label.setStyleSheet("""
                QLabel {
                    color: #666666;
                    font-size: 10px;
                }
            """)
            percentage_label.setAlignment(Qt.AlignCenter)
            medal_group.addWidget(percentage_label)
            
            # Create a widget to hold the vertical layout
            medal_container = QWidget()
            medal_container.setLayout(medal_group)
            medals_layout.addWidget(medal_container)
        
        # Add container to main layout
        main_layout.addWidget(container)
        
    def _get_percentage_text(self, medal_type):
        """Return the percentage range text for each medal type"""
        ranges = {
            "gold": "80%+",
            "silver": "70-79%",
            "bronze": "60-69%"
        }
        return ranges.get(medal_type.lower(), "")
