from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPainter, QColor
from .constants import MEDAL_COLORS

class MedalWidget(QWidget):
    def __init__(self, medal_type: str, count: int):
        super().__init__()
        self.medal_type = medal_type
        self.count = count
        
        # Load the SVG data with the stroke color specified
        self.svg_data = f'''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <path stroke="{MEDAL_COLORS[self.medal_type]}" fill="none" stroke-width="2" d="M17 15.2454V22.1169C17 22.393 16.7761 22.617 16.5 22.617C16.4094 22.617 16.3205 22.5923 16.2428 22.5457L12 20L7.75725 22.5457C7.52046 22.6877 7.21333 22.6109 7.07125 22.3742C7.02463 22.2964 7 22.2075 7 22.1169V15.2454C5.17107 13.7793 4 11.5264 4 9C4 4.58172 7.58172 1 12 1C16.4183 1 20 4.58172 20 9C20 11.5264 18.8289 13.7793 17 15.2454ZM9 16.4185V19.4676L12 17.6676L15 19.4676V16.4185C14.0736 16.7935 13.0609 17 12 17C10.9391 17 9.92643 16.7935 9 16.4185ZM12 15C15.3137 15 18 12.3137 18 9C18 5.68629 15.3137 3 12 3C8.68629 3 6 5.68629 6 9C6 12.3137 8.68629 15 12 15Z"/>
        </svg>
        '''
        
        # Create the SVG renderer
        self.renderer = QSvgRenderer(self.svg_data.encode('utf-8'))
        
        self._setup_ui()
    
    def _setup_ui(self):
        self.setFixedSize(QSize(60, 80))
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 35, 0, 0)
        layout.setSpacing(5)
        
        # Count label
        count_label = QLabel(str(self.count))
        count_label.setMinimumSize(20, 20) 
        count_label.setStyleSheet("""
            QLabel {
                color: black;
                font-size: 16px;
                font-weight: bold;
                padding: 2px;  
            }
        """)
        count_label.setAlignment(Qt.AlignCenter)
        
        # Medal type label
        type_label = QLabel(self.medal_type.capitalize())
        type_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 12px;
            }
        """)
        type_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(count_label)
        layout.addWidget(type_label)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate the size and position for the SVG
        svg_size = 30  # Adjust this value to change the medal size
        x = (self.width() - svg_size) // 2
        y = 5  
        
        # Render the SVG using QRectF
        self.renderer.render(painter, QRectF(x, y, svg_size, svg_size))
        
        # End the painter to avoid the QBackingStore warning
        painter.end()
