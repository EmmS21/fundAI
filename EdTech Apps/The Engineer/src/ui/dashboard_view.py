from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QGridLayout, QLineEdit, QSpinBox, QDialog, QFormLayout, QFileDialog, QSizePolicy, QInputDialog, QProgressBar,
    QLayout, QLayoutItem, QWidgetItem
)
from PySide6.QtCore import Qt, Signal, QRect, QSize, QPoint
from PySide6.QtGui import QFont, QPixmap, QPainter, QPainterPath
import shutil
from pathlib import Path

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, hSpacing=-1, vSpacing=-1):
        super().__init__(parent)
        self.itemList = []
        self.m_hSpace = hSpacing
        self.m_vSpace = vSpacing
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def insertWidget(self, index, widget):
        self.addChildWidget(widget)
        item = QWidgetItem(widget)
        if 0 <= index <= len(self.itemList):
            self.itemList.insert(index, item)
        else:
            self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def doLayout(self, rect, testOnly):
        left, top, right, bottom = self.getContentsMargins()
        effectiveRect = rect.adjusted(left, top, -right, -bottom)
        x = effectiveRect.x()
        y = effectiveRect.y()
        lineHeight = 0

        if not self.itemList:
            return y + lineHeight - rect.y() + bottom

        # Separate profile picture from other items
        profile_item = self.itemList[0] if len(self.itemList) > 0 else None
        other_items = self.itemList[1:] if len(self.itemList) > 1 else []

        # Position profile picture at far left
        if profile_item and not testOnly:
            profile_item.setGeometry(QRect(QPoint(int(x), y), profile_item.sizeHint()))
        
        if profile_item:
            x += profile_item.sizeHint().width()
            lineHeight = max(lineHeight, profile_item.sizeHint().height())

        # If we have other items, distribute them with space-evenly
        if other_items:
            # Add some spacing after profile picture
            profile_spacing = 20  # Fixed spacing after profile picture
            x += profile_spacing
            
            # Calculate total width needed for remaining items
            totalItemWidth = sum(item.sizeHint().width() for item in other_items)
            
            # Calculate available space for distribution
            remainingWidth = effectiveRect.right() - x
            remainingSpace = remainingWidth - totalItemWidth
            
            # Distribute space evenly between remaining items
            if len(other_items) > 1 and remainingSpace > 0:
                spaceBetween = remainingSpace / (len(other_items) + 1)
                x += spaceBetween  # Initial offset
            else:
                spaceBetween = self.horizontalSpacing()

            for i, item in enumerate(other_items):
                if not testOnly:
                    item.setGeometry(QRect(QPoint(int(x), y), item.sizeHint()))

                x += item.sizeHint().width()
                
                # Add space between items (except after the last item)
                if i < len(other_items) - 1:
                    x += spaceBetween
                    
                lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y() + bottom

    def horizontalSpacing(self):
        if self.m_hSpace >= 0:
            return self.m_hSpace
        else:
            return self.smartSpacing(QSizePolicy.PushButton, Qt.Horizontal)

    def verticalSpacing(self):
        if self.m_vSpace >= 0:
            return self.m_vSpace
        else:
            return self.smartSpacing(QSizePolicy.PushButton, Qt.Vertical)

    def smartSpacing(self, pm, orientation):
        parent = self.parent()
        if not parent:
            return -1
        elif parent.isWidgetType():
            return parent.style().layoutSpacing(pm, pm, orientation)
        else:
            return parent.spacing()

class CircularImageWidget(QWidget):
    def __init__(self, size=116, parent=None):
        super().__init__(parent)
        self.size = size
        self.pixmap = None
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        
    def setPixmap(self, pixmap):
        self.pixmap = pixmap
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.pixmap:
            # Create circular clipping path
            path = QPainterPath()
            path.addEllipse(0, 0, self.size, self.size)
            painter.setClipPath(path)
            
            # Draw the image
            painter.drawPixmap(0, 0, self.size, self.size, self.pixmap)
        else:
            # Draw camera icon when no image
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.white)
            painter.setOpacity(0.1)
            painter.drawEllipse(0, 0, self.size, self.size)
            
            # Draw camera icon
            painter.setOpacity(0.7)
            painter.setPen(Qt.white)
            font = painter.font()
            font.setPointSize(self.size // 4)  # 2x bigger than before
            painter.setFont(font)
            
            # Center the camera icon
            painter.drawText(self.rect(), Qt.AlignCenter, "📷")
        
        painter.end()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.upload_profile_picture()
            
    def upload_profile_picture(self):
        """Handle profile picture upload"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Profile Picture",
            "",
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        
        if file_path:
            try:
                # Create profile pictures directory
                profile_dir = Path("data/profile_pictures")
                profile_dir.mkdir(exist_ok=True)
                
                # Copy file to our directory with user ID in filename
                user_id = self.parent().user_data.get('id', 'unknown')
                file_extension = Path(file_path).suffix
                new_filename = f"user_{user_id}_profile{file_extension}"
                new_path = profile_dir / new_filename
                
                # Copy the file
                shutil.copy2(file_path, new_path)
                
                # Update database
                if 'id' in self.parent().user_data:
                    success = self.parent().main_window.database.update_user_profile(
                        self.parent().user_data['id'],
                        profile_picture=str(new_path)
                    )
                    
                    if success:
                        # Update local data
                        self.parent().user_data['profile_picture'] = str(new_path)
                        
                        # Update UI
                        self.parent().load_profile_picture()
                        
                        print(f"Profile picture updated: {new_path}")
                    else:
                        print("Failed to update profile picture in database")
                
            except Exception as e:
                print(f"Error uploading profile picture: {e}")

class ProfileEditDialog(QDialog):
    profile_updated = Signal(dict)
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Profile")
        self.setMinimumSize(300, 200)
        self.user_data = user_data
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Edit Your Profile")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 20px;
            }
        """)
        layout.addWidget(title)
        
        # Form
        form_layout = QFormLayout()
        
        # Name input
        self.name_input = QLineEdit()
        self.name_input.setText(self.user_data.get('username', ''))
        self.name_input.setStyleSheet("""
            QLineEdit {
                font-size: 14px;
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                margin-bottom: 10px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        form_layout.addRow("Name:", self.name_input)
        
        # Age input
        self.age_input = QSpinBox()
        self.age_input.setRange(12, 18)
        self.age_input.setValue(self.user_data.get('age', 15))
        self.age_input.setStyleSheet("""
            QSpinBox {
                font-size: 14px;
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                margin-bottom: 10px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        form_layout.addRow("Age:", self.age_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 10px 20px;
                border: 2px solid #95a5a6;
                border-radius: 5px;
                background-color: white;
                color: #2c3e50;
            }
            QPushButton:hover {
                background-color: #ecf0f1;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        save_button = QPushButton("Save")
        save_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                background-color: #3498db;
                color: white;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        save_button.clicked.connect(self.save_profile)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
    
    def save_profile(self):
        updated_data = {
            'username': self.name_input.text().strip(),
            'age': self.age_input.value()
        }
        
        if updated_data['username']:
            self.profile_updated.emit(updated_data)
            self.accept()

class DashboardView(QWidget):
    def __init__(self, user_data, main_window):
        super().__init__()
        self.user_data = user_data or {}
        self.main_window = main_window
        self.is_editing = False
        self.name_input = None
        self.save_button = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)
        
        # Header section
        header_section = QVBoxLayout()
        header_section.setSpacing(10)
        
        # Title
        welcome_label = QLabel("The Engineer")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: 700;
                color: rgba(255, 255, 255, 0.95);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin-bottom: 5px;
            }
        """)
        header_section.addWidget(welcome_label)
        
        # Subtitle
        subtitle_label = QLabel("The Engineer - learn software engineering by building projects")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 400;
                color: rgba(255, 255, 255, 0.7);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin-bottom: 15px;
            }
        """)
        header_section.addWidget(subtitle_label)
        
        # Divider line
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("""
            QFrame {
                color: rgba(255, 255, 255, 0.2);
                background-color: rgba(255, 255, 255, 0.2);
                border: none;
                height: 1px;
                margin: 10px 0px;
            }
        """)
        header_section.addWidget(divider)
        
        layout.addLayout(header_section)
        
        # Save button container (will be populated when editing)
        self.header_layout = QHBoxLayout()
        self.header_layout.addStretch()
        layout.addLayout(self.header_layout)
        
        profile_frame = QFrame()
        profile_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 25px;
            }
        """)
        
        self.profile_layout = FlowLayout(profile_frame, margin=0, hSpacing=15, vSpacing=10)
        
        self.profile_picture = CircularImageWidget(90)
        self.load_profile_picture()
        self.profile_layout.addWidget(self.profile_picture)
        
        self.name_value = QLabel(self.user_data.get('username', 'Student'))
        self.name_value.setWordWrap(True)
        self.name_value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.name_value.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
        self.name_value.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.95);
                font-size: 16px;
                font-weight: 600;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QLabel:hover {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 4px;
                padding: 4px;
            }
        """)
        self.name_value.setCursor(Qt.PointingHandCursor)
        self.name_value.mousePressEvent = self.start_editing_name
        self.profile_layout.addWidget(self.name_value)
        
        score_value = f"{self.user_data.get('overall_score', 0):.1f}%"
        self.score_value = QLabel(score_value)
        self.score_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.score_value.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.score_value.setStyleSheet("""
            QLabel {
                color: rgba(100, 210, 255, 0.9);
                font-size: 18px;
                font-weight: 700;
                font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
            }
        """)
        self.profile_layout.addWidget(self.score_value)
        
        layout.addWidget(profile_frame)
        
        # Two simple QLabel boxes
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)
        
        logic_label = QLabel("🧩 Logic Puzzles")
        logic_label.setAlignment(Qt.AlignCenter)
        logic_label.setStyleSheet("""
            QLabel {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 20px;
                font-size: 16px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QLabel:hover {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.2);
            }
        """)
        
        build_label = QLabel("🏗️ Build Projects")
        build_label.setAlignment(Qt.AlignCenter)
        build_label.setStyleSheet("""
            QLabel {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 20px;
                font-size: 16px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QLabel:hover {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.2);
            }
        """)
        
        bottom_layout.addWidget(logic_label)
        bottom_layout.addWidget(build_label)
        
        layout.addLayout(bottom_layout)
        
        # Skills Section (no box, just plain text)
        skills_title = QLabel("Engineering Skills Progress")
        skills_title.setAlignment(Qt.AlignCenter)
        skills_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        skills_title.setWordWrap(True)
        skills_title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 25px 0px 15px 0px;
                min-height: 25px;
            }
        """)
        layout.addWidget(skills_title)
        
        skills_divider = QFrame()
        skills_divider.setFrameShape(QFrame.HLine)
        skills_divider.setStyleSheet("""
            QFrame {
                color: rgba(255, 255, 255, 0.2);
                background-color: rgba(255, 255, 255, 0.2);
                border: none;
                height: 1px;
                margin: 10px 0px;
            }
        """)
        layout.addWidget(skills_divider)
        
        # Project stats
        completed_projects = self.get_completed_projects_count()
        in_progress_projects = self.get_in_progress_projects_count()
        total_skills = self.get_total_skills_count()
        
        stats_text = f"🎯 {completed_projects} Completed  •  🚧 {in_progress_projects} In Progress  •  📊 {total_skills} Skills"
        stats_label = QLabel(stats_text)
        stats_label.setAlignment(Qt.AlignCenter)
        stats_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        stats_label.setWordWrap(True)
        stats_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: 500;
                color: rgba(100, 210, 255, 0.8);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin-bottom: 15px;
                min-height: 20px;
            }
        """)
        layout.addWidget(stats_label)
        
        # Skills grid (no container)
        skills_grid = QGridLayout()
        skills_grid.setSpacing(8)
        skills_grid.setSizeConstraint(QGridLayout.SetMinimumSize)
        self.load_skills_data_grid(skills_grid)
        layout.addLayout(skills_grid)

    def start_editing_name(self, event):
        if event.button() == Qt.LeftButton and not self.is_editing:
            self.is_editing = True
            self.show_save_button()
            
            # Remove name label and add input
            current_text = self.name_value.text()
            self.name_value.hide()
            
            # Find the position of name_value in the layout
            name_index = -1
            for i in range(self.profile_layout.count()):
                if self.profile_layout.itemAt(i).widget() == self.name_value:
                    name_index = i
                    break
            
            if name_index >= 0:
                # Remove the name label from layout
                self.profile_layout.takeAt(name_index)
            
            self.name_input = QLineEdit(current_text)
            self.name_input.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.name_input.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            self.name_input.setStyleSheet("""
                QLineEdit {
                    color: rgba(255, 255, 255, 0.95);
                    font-size: 16px;
                    font-weight: 600;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: rgba(255, 255, 255, 0.1);
                    border: 2px solid rgba(100, 210, 255, 0.5);
                    border-radius: 4px;
                    padding: 4px;
                }
            """)
            
            # Insert the input at the same position
            if name_index >= 0:
                self.profile_layout.insertWidget(name_index, self.name_input)
            else:
                self.profile_layout.addWidget(self.name_input)
                
            self.name_input.selectAll()
            self.name_input.setFocus()

    def show_save_button(self):
        if not self.save_button:
            self.save_button = QPushButton("Save Changes")
            self.save_button.setStyleSheet("""
                QPushButton {
                    font-size: 14px;
                    font-weight: 600;
                    padding: 8px 16px;
                    border: 2px solid rgba(100, 210, 255, 0.5);
                    border-radius: 6px;
                    background-color: rgba(100, 210, 255, 0.1);
                    color: rgba(100, 210, 255, 0.9);
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }
                QPushButton:hover {
                    background-color: rgba(100, 210, 255, 0.2);
                    border-color: rgba(100, 210, 255, 0.7);
                }
            """)
            self.save_button.clicked.connect(self.save_changes)
            self.header_layout.addWidget(self.save_button)

    def save_changes(self):
        username = self.user_data.get('username', 'Student')
        
        if self.name_input:
            username = self.name_input.text().strip()
        
        if username and 'id' in self.user_data:
            success = self.main_window.database.update_user_profile(
                self.user_data['id'],
                username=username
            )
            
            if success:
                self.user_data['username'] = username
                print(f"Profile updated: {username}")
        
        self.exit_edit_mode()

    def exit_edit_mode(self):
        self.is_editing = False
        
        # Remove save button
        if self.save_button:
            self.save_button.hide()
            self.header_layout.removeWidget(self.save_button)
            self.save_button.deleteLater()
            self.save_button = None
        
        # Replace input with label
        if self.name_input:
            # Find the position of name_input in the layout
            input_index = -1
            for i in range(self.profile_layout.count()):
                if self.profile_layout.itemAt(i).widget() == self.name_input:
                    input_index = i
                    break
            
            if input_index >= 0:
                # Remove the input from layout
                self.profile_layout.takeAt(input_index)
            
            self.name_value.setText(self.user_data.get('username', 'Student'))
            self.name_input.deleteLater()
            self.name_input = None
            
            # Insert the label at the same position
            if input_index >= 0:
                self.profile_layout.insertWidget(input_index, self.name_value)
            else:
                self.profile_layout.addWidget(self.name_value)
                
            self.name_value.show()

    def load_profile_picture(self):
        """Load and display the user's profile picture"""
        picture_path = self.user_data.get('profile_picture', '')
        
        if picture_path and Path(picture_path).exists():
            # Load user's profile picture
            pixmap = QPixmap(picture_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(116, 116, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self.profile_picture.setPixmap(scaled_pixmap)
                return
        
        # Show default avatar - clear the widget
        self.profile_picture.pixmap = None
        self.profile_picture.update()
    
    def create_proper_circular_image(self, source_pixmap, size=116):
        """Create a properly circular cropped image"""
        from PySide6.QtGui import QPainter, QBrush, QPainterPath
        
        # Create final result pixmap
        result = QPixmap(size, size)
        result.fill(Qt.transparent)
        
        # Scale the image to fill the entire circle (crop if needed)
        scaled = source_pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        
        # Center the scaled image if it's larger than the target size
        x = (size - scaled.width()) // 2
        y = (size - scaled.height()) // 2
        
        # Create the painter and set up for circular clipping
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create circular clipping path
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        
        # Draw the image
        painter.drawPixmap(x, y, scaled)
        painter.end()
        
        return result
    
    def load_skills_data(self):
        if 'id' not in self.user_data:
            self.show_no_skills_message()
            return
        
        skills = self.main_window.database.get_user_skills(self.user_data['id'])
        
        if not skills:
            self.show_no_skills_message()
            return
        
        top_skills = skills[:6]
        
        for skill in top_skills:
            skill_widget = self.create_skill_progress_bar(
                skill['skill_name'], 
                skill['current_score'],
                skill['total_evaluations']
            )
            self.skills_container.addWidget(skill_widget)
    
    def load_skills_data_grid(self, grid_layout):
        if 'id' not in self.user_data:
            no_skills_label = QLabel("Complete projects to start tracking your engineering skills!")
            no_skills_label.setAlignment(Qt.AlignCenter)
            no_skills_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            no_skills_label.setWordWrap(True)
            no_skills_label.setStyleSheet("""
                QLabel {
                    font-size: 13px;
                    color: rgba(255, 255, 255, 0.6);
                    font-style: italic;
                    padding: 15px 5px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    min-height: 20px;
                }
            """)
            grid_layout.addWidget(no_skills_label, 0, 0, 1, 3)
            return
        
        skills = self.main_window.database.get_user_skills(self.user_data['id'])
        
        if not skills:
            no_skills_label = QLabel("Complete projects to start tracking your engineering skills!")
            no_skills_label.setAlignment(Qt.AlignCenter)
            no_skills_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            no_skills_label.setWordWrap(True)
            no_skills_label.setStyleSheet("""
                QLabel {
                    font-size: 13px;
                    color: rgba(255, 255, 255, 0.6);
                    font-style: italic;
                    padding: 15px 5px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    min-height: 20px;
                }
            """)
            grid_layout.addWidget(no_skills_label, 0, 0, 1, 3)
            return
        
        # Take top 6 skills and arrange in 3x2 grid
        top_skills = skills[:6]
        
        for i, skill in enumerate(top_skills):
            row = i // 3
            col = i % 3
            
            skill_text = f"{self.format_skill_name(skill['skill_name'])}: {skill['current_score']:.0f}%"
            skill_label = QLabel(skill_text)
            skill_label.setAlignment(Qt.AlignCenter)
            skill_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            skill_label.setWordWrap(True)
            skill_label.setMinimumHeight(40)
            skill_label.setMaximumHeight(60)
            skill_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    font-weight: 500;
                    color: rgba(255, 255, 255, 0.9);
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    padding: 8px 6px;
                    background: rgba(255, 255, 255, 0.08);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 8px;
                    margin: 2px;
                }
                QLabel:hover {
                    background: rgba(255, 255, 255, 0.12);
                    border-color: rgba(255, 255, 255, 0.25);
                }
            """)
            grid_layout.addWidget(skill_label, row, col)
    
    def show_no_skills_message(self):
        no_skills_label = QLabel("Complete projects to start tracking your engineering skills!")
        no_skills_label.setAlignment(Qt.AlignCenter)
        no_skills_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.6);
                font-style: italic;
                padding: 20px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
        """)
        # self.skills_container.addWidget(no_skills_label) # This line is removed as per the edit hint
    
    def create_skill_progress_bar(self, skill_name, score, evaluations):
        skill_widget = QWidget()
        skill_layout = QHBoxLayout(skill_widget)
        skill_layout.setContentsMargins(0, 0, 0, 0)
        skill_layout.setSpacing(0)
        
        # Create a simple text display: "Skill Name: 85%"
        skill_text = f"{self.format_skill_name(skill_name)}: {score:.0f}%"
        skill_label = QLabel(skill_text)
        skill_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 500;
                color: rgba(255, 255, 255, 0.9);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 8px 0px;
            }
        """)
        skill_layout.addWidget(skill_label)
        
        return skill_widget
    
    def format_skill_name(self, skill_name):
        return skill_name.replace('_', ' ').title()
    
    def get_completed_projects_count(self):
        if 'id' not in self.user_data:
            return 0
        
        try:
            cursor = self.main_window.database.connection.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM github_projects 
                WHERE user_id = ? AND completed_at IS NOT NULL
            """, (self.user_data['id'],))
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception:
            return 0
    
    def get_in_progress_projects_count(self):
        if 'id' not in self.user_data:
            return 0
        
        try:
            cursor = self.main_window.database.connection.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM github_projects 
                WHERE user_id = ? AND completed_at IS NULL
            """, (self.user_data['id'],))
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception:
            return 0
    
    def get_total_skills_count(self):
        if 'id' not in self.user_data:
            return 0
        
        try:
            cursor = self.main_window.database.connection.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM user_skills WHERE user_id = ?
            """, (self.user_data['id'],))
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception:
            return 0
    
    def create_stat_widget(self, title, value, icon):
        stat_widget = QWidget()
        stat_layout = QVBoxLayout(stat_widget)
        stat_layout.setAlignment(Qt.AlignCenter)
        stat_layout.setSpacing(5)
        
        # Simple value display
        value_label = QLabel(f"{icon} {value}")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: 600;
                color: rgba(100, 210, 255, 0.9);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
        """)
        stat_layout.addWidget(value_label)
        
        # Title
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: 500;
                color: rgba(255, 255, 255, 0.7);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
        """)
        stat_layout.addWidget(title_label)
        
        return stat_widget 