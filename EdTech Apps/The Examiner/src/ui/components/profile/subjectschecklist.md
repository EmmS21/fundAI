# Subject Feature Implementation Checklist

## Layout & Positioning
- [x] Move "My Subjects" title to left alignment with 20px margin
- [x] Position "Add Subject" button below title with same 20px left margin
- [x] Update "Add Subject" button styling:
  - [x] Change background color to #A855F7
  - [x] Add hover state (#9333EA)
  - [x] Update padding (12px vertical, 16px horizontal)
  - [x] Keep existing border radius and text styling

## Subject Dropdown (QComboBox)
- [x] Update dropdown styling:
  - [x] White background
  - [x] Light gray border (#E5E7EB)
  - [x] 8px border radius
  - [x] Add subtle drop shadow
  - [x] Update font to 14px #374151
- [x] Position dropdown directly under Add Subject button
- [x] Add hover state for dropdown items
- [x] Ensure dropdown closes after selection

## Subject Cards
- [ ] Create card container for each subject:
  - [ ] White background
  - [ ] 8px border radius
  - [ ] Light border (#E5E7EB)
  - [ ] 16px padding
- [ ] Style subject name:
  - [ ] Left align
  - [ ] 16px font size
  - [ ] Bold weight
  - [ ] Color #1F2937
- [ ] Add delete button:
  - [ ] Position in top-right
  - [ ] Add hover state
  - [ ] Add delete icon
- [ ] Maintain 12px spacing between cards

## Level Selection
- [ ] Add checkbox row below subject name
- [ ] Create three checkboxes:
  - [ ] Grade 7
  - [ ] O Level
  - [ ] A Level
- [ ] Style checkboxes:
  - [ ] 16px size
  - [ ] Purple accent (#A855F7) when checked
  - [ ] Light gray border (#D1D5DB) when unchecked
  - [ ] 4px border radius
- [ ] Add 16px spacing between checkboxes
- [ ] Left align checkbox row
- [ ] Add hover states

## Database Integration
- [x] Create/update subjects table with fields:
  - [x] Subject name
  - [ ] Selected state
  - [ ] Grade 7 checkbox state
  - [ ] O Level checkbox state
  - [ ] A Level checkbox state
  - [x] Creation timestamp
- [x] Add database operations:
  - [x] Add new subject
  - [x] Delete subject
  - [ ] Update checkbox states
  - [x] Retrieve subject list
- [x] Ensure deleted subjects return to dropdown

## Testing
- [x] Test subject addition flow
- [x] Test subject deletion flow
- [ ] Verify checkbox state persistence
- [x] Check dropdown behavior
- [x] Validate database operations
- [x] Test UI responsiveness
