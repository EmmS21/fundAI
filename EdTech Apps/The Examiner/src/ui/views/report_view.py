import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
                               QFrame, QPushButton, QProgressBar, QSpacerItem, QSizePolicy,
                               QGraphicsOpacityEffect)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont

from src.ui.components.profile.achievements.medal_widget import MedalWidget
from src.data.database.operations import UserOperations
from src.data.database.models import User, ExamResult, QuestionResponse 
import json # Add for parsing user_answer_json
from datetime import datetime # Add for parsing timestamp

logger = logging.getLogger(__name__)

class QuestionNumberCircle(QWidget):
    def __init__(self, number: int, parent=None):
        super().__init__(parent)
        self.number = number
        self.setFixedSize(24, 24)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor("#6B7280"))) 
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 22, 22)

        painter.setPen(QPen(Qt.white))
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, str(self.number))
        painter.end()

class AnswerTextWidget(QWidget):
    def __init__(self, text: str, border_color: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(5)

        self.border_line = QFrame()
        self.border_line.setFixedWidth(3)
        self.border_line.setStyleSheet(f"background-color: {border_color};")

        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet("font-size: 14px; color: #374151;")

        layout.addWidget(self.border_line)
        layout.addWidget(self.text_label)
        self.setLayout(layout)

class QuestionAnswerItemWidget(QFrame):
    def __init__(self, question_number: int, question_text: str, student_answer: str,
                 correct_answer: str, ai_feedback: str, parent=None):
        super().__init__(parent)
        self.setObjectName("qaItem")
        self.setStyleSheet("""
            QFrame#qaItem {
                border: none;
                border-top: 1px solid #E5E7EB; /* Separator line, added color */
                padding-top: 15px;
                padding-bottom: 15px;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 15, 10, 15)
        main_layout.setSpacing(10)

        # Question Header (Number + Text)
        question_header_layout = QHBoxLayout()
        question_header_layout.setSpacing(10)
        
        self.q_num_circle = QuestionNumberCircle(question_number)
        question_header_layout.addWidget(self.q_num_circle, alignment=Qt.AlignTop)

        self.question_label = QLabel(question_text)
        self.question_label.setStyleSheet("font-size: 15px; color: #1F2937; font-weight: 500;")
        self.question_label.setWordWrap(True)
        question_header_layout.addWidget(self.question_label)
        main_layout.addLayout(question_header_layout)

        # Student Answer
        self.your_answer_title = QLabel("Your Answer:")
        self.your_answer_title.setStyleSheet("font-size: 12px; color: #6B7280; margin-left: 34px;") # Aligned with question text
        main_layout.addWidget(self.your_answer_title)
        self.student_answer_widget = AnswerTextWidget(student_answer, "#3B82F6") # Blue border
        main_layout.addWidget(self.student_answer_widget, 0, Qt.AlignLeft | Qt.AlignVCenter)


        # Correct Answer
        self.correct_answer_title = QLabel("Correct Answer:")
        self.correct_answer_title.setStyleSheet("font-size: 12px; color: #6B7280; margin-left: 34px;")
        main_layout.addWidget(self.correct_answer_title)
        self.correct_answer_widget = AnswerTextWidget(correct_answer, "#10B981") # Green border
        main_layout.addWidget(self.correct_answer_widget, 0, Qt.AlignLeft | Qt.AlignVCenter)

        # AI Feedback
        if ai_feedback:
            self.ai_feedback_title = QLabel("AI Feedback:")
            self.ai_feedback_title.setStyleSheet("font-size: 12px; color: #6B7280; margin-left: 34px;")
            main_layout.addWidget(self.ai_feedback_title)
            self.ai_feedback_label = QLabel(ai_feedback)
            self.ai_feedback_label.setWordWrap(True)
            self.ai_feedback_label.setStyleSheet("font-size: 14px; color: #4B5563; margin-left: 34px; background-color: #F9FAFB; padding: 8px; border-radius: 4px;")
            main_layout.addWidget(self.ai_feedback_label)
        
        self.setLayout(main_layout)

class ReportView(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #F3F4F6;")

        self.main_scroll_area = QScrollArea(self)
        self.main_scroll_area.setWidgetResizable(True)
        self.main_scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.page_content_widget = QWidget() 
        self.page_content_widget.setStyleSheet("background-color: white; margin: 20px; border-radius: 8px;")
        self.main_scroll_area.setWidget(self.page_content_widget)

        content_layout = QVBoxLayout(self.page_content_widget) 
        content_layout.setContentsMargins(25, 25, 25, 25) 
        content_layout.setSpacing(15)

        # --- Top Navigation Bar (with Back Button) ---
        top_nav_layout = QHBoxLayout()
        top_nav_layout.setContentsMargins(0, 0, 0, 10)

        self.back_button = QPushButton("← Back to Profile")
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                color: #4B5563;
                background-color: #F3F4F6; 
                border: 1px solid #E5E7EB; 
                border-radius: 6px;
                padding: 6px 12px; /* Vertical padding of 6px top & bottom */
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #E5E7EB;
                border-color: #D1D5DB;
            }
        """)
        self.back_button.clicked.connect(self.back_requested.emit)
        
        top_nav_layout.addWidget(self.back_button, 0, Qt.AlignLeft)
        top_nav_layout.addStretch(1) 
        content_layout.addLayout(top_nav_layout) 

        # --- Header (Student, Date, Report Status) ---
        header_layout = QHBoxLayout()
        self.student_name_label = QLabel("Student: N/A")
        self.student_name_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #6D28D9;")
        
        self.exam_date_label = QLabel("Date: N/A")
        self.exam_date_label.setStyleSheet("font-size: 14px; color: #6B7280;")

        self.report_status_label = QLabel("Status: N/A") 
        self.report_status_label.setStyleSheet("font-size: 14px; color: #6B7280; font-style: italic;")

        header_layout.addWidget(self.student_name_label)
        header_layout.addStretch()
        header_layout.addWidget(self.report_status_label) 
        header_layout.addWidget(self.exam_date_label)
        content_layout.addLayout(header_layout)

        # --- Score Section ---
        score_section_frame = QFrame() 
        score_section_layout = QHBoxLayout(score_section_frame)
        score_section_layout.setContentsMargins(0,0,0,0)
        score_section_layout.setSpacing(20)

        score_details_layout = QVBoxLayout()
        score_details_layout.setSpacing(5)
        self.assessment_score_title = QLabel("Assessment Score")
        self.assessment_score_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1F2937;")
        
        progress_layout = QHBoxLayout()
        self.score_progress_bar = QProgressBar()
        self.score_progress_bar.setFixedHeight(20)
        self.score_progress_bar.setTextVisible(False)
        self.score_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #D1D5DB;
                border-radius: 10px;
                background-color: #E5E7EB;
            }
            QProgressBar::chunk {
                background-color: #8B5CF6;
                border-radius: 9px;
            }
        """)
        self.score_percentage_label = QLabel("0%")
        self.score_percentage_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1F2937;")
        progress_layout.addWidget(self.score_progress_bar, 1) 
        progress_layout.addWidget(self.score_percentage_label, 0, Qt.AlignRight) 
        
        score_details_layout.addWidget(self.assessment_score_title)
        score_details_layout.addLayout(progress_layout)
        score_section_layout.addLayout(score_details_layout, 2)

        # --- Medal Display Area ---
        self.medal_display_area = QWidget() # Container for all medals and fail label
        medal_area_overall_layout = QVBoxLayout(self.medal_display_area)
        medal_area_overall_layout.setContentsMargins(0,0,0,0)
        medal_area_overall_layout.setSpacing(5) # Spacing between medal row and fail label
        medal_area_overall_layout.setAlignment(Qt.AlignCenter)

        medals_row_layout = QHBoxLayout() # For Gold, Silver, Bronze side-by-side
        medals_row_layout.setSpacing(15)

        self.gold_medal_widget = MedalWidget("gold", 0) # Count 0 initially, text might be hidden
        self.silver_medal_widget = MedalWidget("silver", 0)
        self.bronze_medal_widget = MedalWidget("bronze", 0)
        
        # Opacity effects for dimming
        self.gold_opacity_effect = QGraphicsOpacityEffect(opacity=0.3)
        self.silver_opacity_effect = QGraphicsOpacityEffect(opacity=0.3)
        self.bronze_opacity_effect = QGraphicsOpacityEffect(opacity=0.3)

        self.gold_medal_widget.setGraphicsEffect(self.gold_opacity_effect)
        self.silver_medal_widget.setGraphicsEffect(self.silver_opacity_effect)
        self.bronze_medal_widget.setGraphicsEffect(self.bronze_opacity_effect)
        
        # Adjust medal sizes if necessary for ReportView
        medal_fixed_size = QSize(50, 60) # Smaller medals for the row
        self.gold_medal_widget.setFixedSize(medal_fixed_size)
        self.silver_medal_widget.setFixedSize(medal_fixed_size)
        self.bronze_medal_widget.setFixedSize(medal_fixed_size)
        
        # Hide count label within MedalWidget if desired for this view (optional)
        # This would require MedalWidget to expose its count_label or have a method for it.
        # For now, count will show 0 or 1.

        medals_row_layout.addWidget(self.bronze_medal_widget) # Order: Bronze, Silver, Gold
        medals_row_layout.addWidget(self.silver_medal_widget)
        medals_row_layout.addWidget(self.gold_medal_widget)
        
        medal_area_overall_layout.addLayout(medals_row_layout)

        self.fail_label = QLabel("FAIL")
        self.fail_label.setStyleSheet("font-size: 16px; font-weight: bold; color: red;")
        self.fail_label.setAlignment(Qt.AlignCenter)
        self.fail_label.setVisible(False) # Initially hidden
        medal_area_overall_layout.addWidget(self.fail_label)
        
        score_section_layout.addWidget(self.medal_display_area, 1) 
        content_layout.addWidget(score_section_frame)

        # --- Questions & Answers Title ---
        self.qa_title_label = QLabel("Questions & Answers")
        self.qa_title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1F2937; margin-top: 10px;")
        content_layout.addWidget(self.qa_title_label)

        # --- Questions Scroll Area ---
        self.qa_scroll_area = QScrollArea()
        self.qa_scroll_area.setWidgetResizable(True)
        self.qa_scroll_area.setStyleSheet("QScrollArea { border: none; background-color: white; }")
        # Set vertical policy to allow expansion but not demand all space from parent scroll view
        self.qa_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)


        self.qa_list_widget = QWidget() 
        self.qa_list_widget.setStyleSheet("background-color: white;")
        self.qa_layout = QVBoxLayout(self.qa_list_widget)
        self.qa_layout.setContentsMargins(0,0,0,0)
        self.qa_layout.setSpacing(0) 
        self.qa_scroll_area.setWidget(self.qa_list_widget)
        content_layout.addWidget(self.qa_scroll_area) # No stretch factor, let MainScrollArea handle overall scroll

        # Main layout for ReportView
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0,0,0,0)
        outer_layout.addWidget(self.main_scroll_area)
        self.setLayout(outer_layout)

    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    sub_layout = item.layout()
                    if sub_layout is not None:
                        self._clear_layout(sub_layout)
    
    def _update_medal(self, percentage_score: float):
        # Default all to dimmed
        self.gold_opacity_effect.setOpacity(0.3)
        self.silver_opacity_effect.setOpacity(0.3)
        self.bronze_opacity_effect.setOpacity(0.3)
        
        self.gold_medal_widget.update_display_text("")
        self.silver_medal_widget.update_display_text("")
        self.bronze_medal_widget.update_display_text("")


        achieved_medal = None
        achieved_text = "✓" # Text for achieved medal

        if percentage_score >= 80: # Gold
            achieved_medal = "gold"
            self.gold_opacity_effect.setOpacity(1.0)
            self.gold_medal_widget.update_display_text(achieved_text)
        elif percentage_score >= 70: # Silver
            achieved_medal = "silver"
            self.silver_opacity_effect.setOpacity(1.0)
            self.silver_medal_widget.update_display_text(achieved_text)
        elif percentage_score >= 60: # Bronze
            achieved_medal = "bronze"
            self.bronze_opacity_effect.setOpacity(1.0)
            self.bronze_medal_widget.update_display_text(achieved_text)

        if percentage_score < 50:
            self.fail_label.setVisible(True)
            # Ensure all medals are dimmed if "Fail"
            self.gold_opacity_effect.setOpacity(0.3)
            self.silver_opacity_effect.setOpacity(0.3)
            self.bronze_opacity_effect.setOpacity(0.3)
        else:
            self.fail_label.setVisible(False)


    def load_report(self, response_id: int): # response_id is the history_id
        logger.info(f"ReportView: Loading report for history_id {response_id}")
        
        # Get the detailed report item for the given history_id
        report_item_details = UserOperations.get_single_report_item_details(response_id)
        current_user_data = UserOperations.get_current_user() # Get current user separately

        if not report_item_details or not current_user_data:
            logger.error(f"Could not load full report data for history_id {response_id}")
            self._clear_layout(self.qa_layout)
            error_label = QLabel("Could not load report details.")
            error_label.setAlignment(Qt.AlignCenter)
            self.qa_layout.addWidget(error_label)
            self.student_name_label.setText("Student: Error")
            self.exam_date_label.setText("Date: Error")
            self.score_percentage_label.setText("-")
            self.score_progress_bar.setValue(0)
            self._update_medal(0)
            return

        # --- Populate Header ---
        self.student_name_label.setText(f"Student: {current_user_data.get('full_name', 'N/A')}")
        try:
            exam_dt = datetime.fromisoformat(report_item_details.get("timestamp", ""))
            self.exam_date_label.setText(f"Date: {exam_dt.strftime('%B %d, %Y %I:%M %p')}")
        except ValueError:
            self.exam_date_label.setText(f"Date: N/A")
        
        # ADDED: Set Report Status Label
        is_final_report = report_item_details.get("is_final", False)
        if is_final_report:
            self.report_status_label.setText("Status: Final Report")
            self.report_status_label.setStyleSheet("font-size: 14px; color: #10B981; font-weight: bold;") # Green for final
        else:
            self.report_status_label.setText("Status: Preliminary Report")
            self.report_status_label.setStyleSheet("font-size: 14px; color: #F59E0B; font-weight: bold;") # Amber for preliminary


        # --- Populate Score (from the single question's AI grade and total marks) ---
        score = report_item_details.get("ai_grade", 0.0)
        if not isinstance(score, (int, float)): # Ensure score is numeric
            try:
                score = float(score) if score else 0.0
            except (ValueError, TypeError):
                score = 0.0
        
        total_possible = report_item_details.get("question_total_marks", 0)
        if not isinstance(total_possible, (int, float)) or total_possible <= 0: # Ensure total_possible is valid
            total_possible = 100 # Default to 100 if invalid to avoid division by zero
            logger.warning(f"Invalid or zero question_total_marks for history_id {response_id}. Defaulting to 100 for percentage calculation.")


        percentage_score = 0
        if total_possible > 0:
            percentage_score = (score / total_possible) * 100
        
        self.score_percentage_label.setText(f"{percentage_score:.0f}%")
        self.score_progress_bar.setValue(int(percentage_score))
        self._update_medal(percentage_score)

        # --- Populate Questions & Answers (for the single question) ---
        self._clear_layout(self.qa_layout) 

        student_answer_text = "N/A"
        if report_item_details.get("user_answer"):
            # Assuming user_answer is a dict like {"selected_option": "A", "written_answer": "Some text"}
            # This needs to be adapted to your actual user_answer_json structure
            answer_detail = report_item_details["user_answer"]
            if isinstance(answer_detail, dict):
                 # Prioritize a 'written_answer' or 'text' field if available
                if 'written_answer' in answer_detail:
                    student_answer_text = str(answer_detail['written_answer'])
                elif 'text' in answer_detail:
                     student_answer_text = str(answer_detail['text'])
                elif 'selected_option' in answer_detail: # Fallback to selected_option
                    student_answer_text = f"Selected: {answer_detail['selected_option']}"
                else: # If structure is unknown, dump the dict
                    student_answer_text = json.dumps(answer_detail)
            else: # If it's not a dict (e.g., just a string), use it directly
                student_answer_text = str(answer_detail)
        
        item_widget = QuestionAnswerItemWidget(
            question_number=1, # Only one question in this view
            question_text=report_item_details.get("question_text", "N/A"),
            student_answer=student_answer_text,
            correct_answer=report_item_details.get("correct_answer", "N/A"), # From _extract_correct_answer
            ai_feedback=report_item_details.get("ai_feedback", "") 
        )
        self.qa_layout.addWidget(item_widget)
        
        self.qa_layout.addStretch(1) 
        self.qa_list_widget.adjustSize() 
        self.qa_scroll_area.verticalScrollBar().setValue(0)
