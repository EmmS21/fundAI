import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
                               QFrame, QPushButton, QProgressBar, QSpacerItem, QSizePolicy,
                               QGraphicsOpacityEffect, QCheckBox)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont

from src.ui.components.profile.achievements.medal_widget import MedalWidget
from src.data.database.operations import UserOperations
from src.data.database.models import User, ExamResult, QuestionResponse 
import json # Add for parsing user_answer_json
from datetime import datetime # Add for parsing timestamp
from typing import Optional, Dict

from src.core import services # <<<< ADD THIS IMPORT

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
        self.current_report_data: Optional[Dict] = None # To store all fetched data
        self.current_view_type = 'final' # Default to 'final', can be 'preliminary'

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
        
        # ADDED: Toggle for Preliminary/Final Report
        self.report_type_toggle_checkbox = QCheckBox("Show Preliminary Report")
        self.report_type_toggle_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 13px;
                color: #4B5563;
                spacing: 5px;
                padding: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked {
                image: url(src/ui/assets/icons/checkbox_unchecked.svg); /* Replace with your icon path */
            }
            QCheckBox::indicator:checked {
                image: url(src/ui/assets/icons/checkbox_checked.svg); /* Replace with your icon path */
            }
        """)
        self.report_type_toggle_checkbox.setVisible(False) # Initially hidden, shown if both reports exist
        self.report_type_toggle_checkbox.toggled.connect(self._on_report_type_toggled)
        top_nav_layout.addWidget(self.report_type_toggle_checkbox, 0, Qt.AlignRight) # Add to the right

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

        # ADDED: Study Topics Section (initially empty)
        self.study_topics_title_label = QLabel("Key Study Topics & Guiding Questions:")
        self.study_topics_title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1F2937; margin-top: 15px;")
        self.study_topics_title_label.setVisible(False)
        content_layout.addWidget(self.study_topics_title_label)

        self.study_topics_content_label = QLabel("")
        self.study_topics_content_label.setWordWrap(True)
        self.study_topics_content_label.setStyleSheet("font-size: 14px; color: #4B5563; background-color: #F9FAFB; padding: 10px; border-radius: 4px; margin-top: 5px;")
        self.study_topics_content_label.setVisible(False)
        self.study_topics_content_label.setTextInteractionFlags(Qt.TextSelectableByMouse) # Allow text selection
        content_layout.addWidget(self.study_topics_content_label)

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
        
        self.current_report_data = UserOperations.get_single_report_item_details(response_id)
        current_user_data = UserOperations.get_current_user()

        if not self.current_report_data or not current_user_data:
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
            self.report_type_toggle_checkbox.setVisible(False)
            self.study_topics_title_label.setVisible(False)
            self.study_topics_content_label.setVisible(False)
            return

        # Mark as viewed (if cloud report and not yet viewed)
        if self.current_report_data.get("has_cloud_report") and not self.current_report_data.get("cloud_report_viewed_timestamp"):
            if services.user_history_manager:
                logger.debug(f"Attempting to mark report {response_id} as viewed.")
                marked_as_viewed = services.user_history_manager.mark_report_as_viewed(response_id) 
                if marked_as_viewed: 
                    logger.info(f"Report {response_id} marked as viewed. Requesting badge update.")
                    main_window = self.window()
                    if main_window and hasattr(main_window, 'profile_info_widget') and \
                       main_window.profile_info_widget and \
                       hasattr(main_window.profile_info_widget, 'subject_selector') and \
                       main_window.profile_info_widget.subject_selector:
                        main_window.profile_info_widget.subject_selector.refresh_badges()
                    else:
                        logger.warning("ReportView: Could not find path to refresh subject card badges after marking as viewed.")
            else:
                logger.error("UserHistoryManager service not available. Cannot mark report as viewed.")

        self.student_name_label.setText(f"Student: {current_user_data.get('full_name', 'N/A')}")
        try:
            exam_dt = datetime.fromisoformat(self.current_report_data.get("timestamp", ""))
            self.exam_date_label.setText(f"Date: {exam_dt.strftime('%B %d, %Y %I:%M %p')}")
        except (ValueError, TypeError):
            self.exam_date_label.setText(f"Date: N/A")
        
        # Determine default view type and manage toggle visibility
        can_show_preliminary = self.current_report_data.get("has_local_report_data", False)
        can_show_final = self.current_report_data.get("has_cloud_report", False)

        if can_show_final and can_show_preliminary:
            self.report_type_toggle_checkbox.setVisible(True)
            # Default to showing final if available, ensure checkbox reflects this
            self.current_view_type = 'final'
            self.report_type_toggle_checkbox.setChecked(False) # Unchecked = Show Final Report
            self.report_type_toggle_checkbox.setText("Show Preliminary Insights")
        elif can_show_final:
            self.current_view_type = 'final'
            self.report_type_toggle_checkbox.setVisible(False)
        elif can_show_preliminary:
            self.current_view_type = 'preliminary'
            self.report_type_toggle_checkbox.setVisible(False)
        else: # No data for either
            self.current_view_type = 'none'
            self.report_type_toggle_checkbox.setVisible(False)
            # Display error or clear fields if no data type is available (already handled by initial check)
            # For safety, explicitly call populate with 'none' or handle clearing here.
            self._populate_report_display() # Will show N/A if no data
            return
            
        self._populate_report_display()

    def _on_report_type_toggled(self, checked: bool):
        if checked: # Checkbox is checked, meaning user wants to see Preliminary
            self.current_view_type = 'preliminary'
            self.report_type_toggle_checkbox.setText("Show Full Report")
        else: # Checkbox is unchecked, meaning user wants to see Final
            self.current_view_type = 'final'
            self.report_type_toggle_checkbox.setText("Show Preliminary Insights")
        self._populate_report_display()

    def _format_study_topics(self, topics_data: Optional[Dict]) -> str:
        if not topics_data:
            return "No specific study topics provided."

        content = []
        if isinstance(topics_data, dict): # New structured format
            if topics_data.get("specific_topics"):
                content.append("<b>Specific Topics:</b>")
                content.extend([f"• {topic}" for topic in topics_data["specific_topics"]])
            if topics_data.get("guiding_questions"):
                if content: content.append("<br>") # Add space if there were previous topics
                content.append("<b>Guiding Questions:</b>")
                content.extend([f"• {q}" for q in topics_data["guiding_questions"]])
            if topics_data.get("search_terms"):
                if content: content.append("<br>")
                content.append("<b>Google Search Terms:</b>")
                content.extend([f"• {s}" for s in topics_data["search_terms"]])
            if topics_data.get("raw") and not (topics_data.get("specific_topics") or topics_data.get("guiding_questions") or topics_data.get("search_terms")):
                # Only show raw if no structured data was parsed
                content.append("<b>Further Details:</b>")
                content.append(topics_data["raw"])
        elif isinstance(topics_data, str): # Fallback for old raw string format
             content.append("<b>Further Details:</b>")
             content.append(topics_data)


        return "<br>".join(content) if content else "No specific study topics provided."


    def _populate_report_display(self):
        if not self.current_report_data:
            # This case should ideally be caught by load_report earlier
            logger.warning("Attempted to populate report display with no data.")
            self.report_status_label.setText("Status: Error Loading Data")
            # Clear other fields...
            self.score_percentage_label.setText("-")
            self.score_progress_bar.setValue(0)
            self._update_medal(0)
            self._clear_layout(self.qa_layout)
            self.qa_layout.addWidget(QLabel("Report data unavailable."))
            self.study_topics_title_label.setVisible(False)
            self.study_topics_content_label.setVisible(False)
            return

        ai_grade_to_display = None
        ai_feedback_to_display = "N/A"
        study_topics_to_display = None
        report_status_text = "Status: N/A"
        report_status_stylesheet = "font-size: 14px; color: #6B7280; font-style: italic;" # Default

        if self.current_view_type == 'final' and self.current_report_data.get("has_cloud_report"):
            ai_grade_to_display = self.current_report_data.get("cloud_ai_grade")
            ai_feedback_to_display = self.current_report_data.get("cloud_ai_rationale", "Feedback not available.")
            study_topics_to_display = self.current_report_data.get("cloud_ai_study_topics")
            report_status_text = "Status: Full Report (Cloud AI)"
            report_status_stylesheet = "font-size: 14px; color: #10B981; font-weight: bold;"
        elif self.current_view_type == 'preliminary' and self.current_report_data.get("has_local_report_data"):
            ai_grade_to_display = self.current_report_data.get("local_ai_grade")
            ai_feedback_to_display = self.current_report_data.get("local_ai_rationale", "Feedback not available.")
            study_topics_to_display = self.current_report_data.get("local_ai_study_topics") # Fetch local study topics
            report_status_text = "Status: Preliminary Insights (Local AI)"
            report_status_stylesheet = "font-size: 14px; color: #F59E0B; font-weight: bold;"
        elif self.current_report_data.get("has_cloud_report"): # Fallback to final if current_view_type is invalid but final exists
            ai_grade_to_display = self.current_report_data.get("cloud_ai_grade")
            ai_feedback_to_display = self.current_report_data.get("cloud_ai_rationale", "Feedback not available.")
            study_topics_to_display = self.current_report_data.get("cloud_ai_study_topics")
            report_status_text = "Status: Full Report (Cloud AI)"
            report_status_stylesheet = "font-size: 14px; color: #10B981; font-weight: bold;"
            self.report_type_toggle_checkbox.setChecked(False) # Sync checkbox
            self.current_view_type = 'final' # Correct the view type
        elif self.current_report_data.get("has_local_report_data"): # Fallback to preliminary if only local exists
            ai_grade_to_display = self.current_report_data.get("local_ai_grade")
            ai_feedback_to_display = self.current_report_data.get("local_ai_rationale", "Feedback not available.")
            study_topics_to_display = self.current_report_data.get("local_ai_study_topics")
            report_status_text = "Status: Preliminary Insights (Local AI)"
            report_status_stylesheet = "font-size: 14px; color: #F59E0B; font-weight: bold;"
            self.report_type_toggle_checkbox.setChecked(True) # Sync checkbox
            self.current_view_type = 'preliminary' # Correct the view type
        else: # No report data of any kind
            self.report_status_label.setText("Status: Report Data Unavailable")
            self.score_percentage_label.setText("-")
            self.score_progress_bar.setValue(0)
            self._update_medal(0)
            self._clear_layout(self.qa_layout)
            self.qa_layout.addWidget(QLabel("No AI feedback available for this item."))
            self.study_topics_title_label.setVisible(False)
            self.study_topics_content_label.setVisible(False)
            return

        self.report_status_label.setText(report_status_text)
        self.report_status_label.setStyleSheet(report_status_stylesheet)

        score = 0.0
        if ai_grade_to_display is not None:
            try:
                score = float(ai_grade_to_display)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert grade '{ai_grade_to_display}' to float for history_id {self.current_report_data.get('history_id')}")
                score = 0.0
        
        total_possible = self.current_report_data.get("question_total_marks", 0)
        if not isinstance(total_possible, (int, float)) or total_possible <= 0:
            total_possible = 100 
            logger.warning(f"Invalid or zero question_total_marks for history_id {self.current_report_data.get('history_id')}. Defaulting to 100.")

        percentage_score = (score / total_possible) * 100 if total_possible > 0 else 0
        
        self.score_percentage_label.setText(f"{percentage_score:.0f}%")
        self.score_progress_bar.setValue(int(percentage_score))
        self._update_medal(percentage_score)

        # --- Populate Questions & Answers ---
        self._clear_layout(self.qa_layout) 

        student_answer_text = "N/A"
        user_answer_data = self.current_report_data.get("user_answer")
        if user_answer_data:
            if isinstance(user_answer_data, dict):
                if 'written_answer' in user_answer_data:
                    student_answer_text = str(user_answer_data['written_answer'])
                elif 'text' in user_answer_data:
                     student_answer_text = str(user_answer_data['text'])
                elif 'selected_option' in user_answer_data:
                    student_answer_text = f"Selected: {user_answer_data['selected_option']}"
                else:
                    student_answer_text = json.dumps(user_answer_data) # Fallback
            else:
                student_answer_text = str(user_answer_data)
        
        item_widget = QuestionAnswerItemWidget(
            question_number=1, 
            question_text=self.current_report_data.get("question_text", "N/A"),
            student_answer=student_answer_text,
            correct_answer=self.current_report_data.get("correct_answer", "N/A"),
            ai_feedback=ai_feedback_to_display
        )
        self.qa_layout.addWidget(item_widget)

        # Study Topics Display
        formatted_study_topics = self._format_study_topics(study_topics_to_display)
        if formatted_study_topics and formatted_study_topics != "No specific study topics provided.":
            self.study_topics_content_label.setText(formatted_study_topics)
            self.study_topics_title_label.setVisible(True)
            self.study_topics_content_label.setVisible(True)
        else:
            self.study_topics_title_label.setVisible(False)
            self.study_topics_content_label.setVisible(False)
        
        self.qa_layout.addStretch(1) 
        self.qa_list_widget.adjustSize() 
        self.qa_scroll_area.verticalScrollBar().setValue(0)
