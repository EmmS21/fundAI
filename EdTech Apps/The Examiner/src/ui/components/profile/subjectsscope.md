# Subjects Feature Scope - Implementation Update

## Current State Analysis

### Visual Layout
1. Add Subject Button:
   - Currently centered in layout with purple background (#7c3aed)
   - Using fixed size of 180x48 pixels
   - Positioned below "My Subjects" header

2. Subject Selection:
   - Using standard QComboBox dropdown
   - Basic styling without custom borders or shadows
   - Default white background

3. Subject Display:
   - Basic list implementation
   - No dedicated subject cards
   - Missing level checkboxes
   - No delete functionality

## Required Changes

### 1. Subject Section Header & Button Layout
Current Issues:
- "My Subjects" title is centered
- Add Subject button is centered below title
- Spacing is inconsistent with design

Required Updates:
- Left-align "My Subjects" title with 20px left margin
- Position "Add Subject" button with 20px left margin (same as title)
- Maintain existing purple theme but update to match design (#A855F7)
- Add subtle hover state to button (#9333EA)
- Update button padding to match design (approximately 12px vertical, 16px horizontal)

### 2. Subject Dropdown Styling
Current Issues:
- Default QComboBox styling doesn't match design
- Missing shadow and border radius
- Incorrect positioning relative to button

Required Updates:
- Keep QComboBox but customize appearance:
  - White background
  - Light gray border (#E5E7EB)
  - 8px border radius
  - Subtle drop shadow (0 2px 4px rgba(0,0,0,0.1))
- Position dropdown directly under Add Subject button
- Add hover states for dropdown items
- Match font size and color to design (14px, #374151)

### 3. Subject Card Implementation
Current Issues:
- Subjects not displayed in card format
- Missing visual hierarchy
- No delete functionality

Required Updates:
- Create card-style containers for each subject:
  - White background
  - 8px border radius
  - Light border (#E5E7EB)
  - 16px padding
- Left-align subject name (16px, bold, #1F2937)
- Add delete button to top-right of each card
- Maintain consistent 12px spacing between cards
- Add subtle hover state for delete button

### 4. Level Selection Implementation
Current Issues:
- Missing level selection functionality
- No visual representation of selected levels

Required Updates:
- Add three checkboxes below subject name:
  - Grade 7
  - O Level
  - A Level
- Style checkboxes to match design:
  - 16px size
  - Purple accent color (#A855F7) when checked
  - Light gray border (#D1D5DB) when unchecked
  - 4px border radius
- Left-align checkboxes with 16px spacing between them
- Add hover states for better interactivity

### 5. Database Integration
Current Requirements:
- Store subject selection state
- Persist level selections (Grade 7, O Level, A Level)
- Track subject creation timestamp for ordering
- Enable subject deletion with state restoration

### 6. Performance & UX Considerations
- Immediate UI feedback on subject addition/deletion
- Smooth animations for dropdown and delete actions
- Efficient database queries for subject list updates
- Proper error handling for database operations

## Success Criteria
1. Visual Accuracy:
   - Layout matches reference design
   - Colors and spacing are consistent
   - Animations feel smooth and natural

2. Functionality:
   - Subjects can be added and deleted
   - Level selections persist
   - Subject list updates immediately
   - All interactions feel responsive

3. Technical:
   - Database operations are efficient
   - No performance degradation with many subjects
   - Error states are handled gracefully

## Implementation Priority
1. Layout and positioning fixes
2. Subject card styling
3. Level selection implementation
4. Database integration
5. Animation and interaction polish

This update focuses on precise visual and functional requirements while maintaining the existing codebase structure. The changes are designed to be incremental and maintain stability while achieving the desired design.
