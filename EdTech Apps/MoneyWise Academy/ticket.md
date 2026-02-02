# 🎫 Ticket: Design and Implement Database Models for MoneyWise Academy

**Assignee:** Junior Developer  
**Difficulty:** 🟡 Medium (Learning Opportunity!)  
**Estimated Time:** 2-3 hours (take your time to understand!)

---

## 📖 What You'll Learn

By completing this ticket, you'll understand:
- What a database is and why we need one
- What "models" are in programming
- Primary keys and foreign keys
- How tables relate to each other
- How to translate a diagram into code

---

## 🤔 Before You Start: Understanding the Basics

### What is a Database?

Think of a database like a **super organized filing cabinet** for your app. Instead of papers in folders, we store information in **tables**. Each table is like a spreadsheet with rows and columns.

**❓ Question 1:** Can you think of 3 apps you use that probably need a database to remember information about you?

---

### What is a Model?

A **model** is like a **blueprint** that describes what information we want to store. It tells the database:
- What "things" we want to keep track of (like Chapters, Questions, Scores)
- What information each "thing" has (like a question has text, an answer, etc.)

**❓ Question 2:** If you were building an app to track your favorite video games, what information would you want to store about each game? (Think of at least 4 things)

---

### What is a Primary Key?

A **Primary Key** is like a **student ID number** - it's a unique identifier that makes sure we can tell one record apart from another.

- Every student at school has a unique ID
- Every book in a library has a unique ISBN
- Every YouTube video has a unique video ID in the URL

**Rules for Primary Keys:**
1. Must be UNIQUE (no two records can have the same one)
2. Cannot be empty (NULL)
3. Should not change once set

**❓ Question 3:** Why do you think it's important that each record has a unique identifier? What problems could happen if two students had the same ID number?

---

### What is a Foreign Key?

A **Foreign Key** is like a **reference** or **link** to another table. It's how we connect related information together.

**Example:** Imagine a school database:
- The `Students` table has: student_id, name, class_id
- The `Classes` table has: class_id, class_name, teacher

The `class_id` in the Students table is a **Foreign Key** - it points to a record in the Classes table.

```
┌─────────────────────┐         ┌─────────────────────┐
│      Students       │         │       Classes       │
├─────────────────────┤         ├─────────────────────┤
│ student_id (PK)     │         │ class_id (PK)       │
│ name                │    ┌───►│ class_name          │
│ class_id (FK) ──────┼────┘    │ teacher             │
└─────────────────────┘         └─────────────────────┘
```

**❓ Question 4:** In the example above, if we delete a class from the Classes table, what should happen to the students that were in that class? (Think about this - there's no single right answer!)

---

## 🎯 Your Mission: MoneyWise Academy Models

MoneyWise Academy is a financial literacy app. Users go through **chapters** to learn about money, answer **questions**, read **study material**, and take **assessments** (tests).

### The Big Picture

```
                         ┌──────────────────┐
                         │  Device/User     │
                         │  hardware_id     │
                         └────────┬─────────┘
                                  │
                                  │ (identifies who this data belongs to)
                                  │
                         ┌────────▼─────────┐
                         │    Progress      │
                         │  (main tracker)  │
                         └────────┬─────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │    Questions    │ │Study Information│ │   Assessment    │
    │  (quiz items)   │ │(learning text)  │ │ (test scores)   │
    └─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## 📋 The Models You Need to Create

### Model 1: Progress

This is the **main tracking table**. It keeps track of which chapters exist and the user's overall progress.

**Purpose:** Track which chapter the user is on and connect all learning data.

```
┌────────────────────────────────────────────────────────┐
│                       Progress                          │
├────────────────────────────────────────────────────────┤
│  chapter_id      │ INTEGER  │ PRIMARY KEY              │
│  hardware_id     │ TEXT     │ Links to user's device   │
│  is_completed    │ BOOLEAN  │ Has user finished?       │
│  started_at      │ DATETIME │ When did they start?     │
│  completed_at    │ DATETIME │ When did they finish?    │
└────────────────────────────────────────────────────────┘
```

**❓ Question 5:** Why do we store `hardware_id` here? (Hint: Think about how the app knows which user's progress this is)

**❓ Question 6:** What data type would you use for `is_completed`? Why?

---

### Model 2: Questions

Stores the questions that users will answer during their learning.

**Purpose:** Store all the quiz/practice questions for each chapter.

```
┌────────────────────────────────────────────────────────┐
│                       Questions                         │
├────────────────────────────────────────────────────────┤
│  question_id     │ INTEGER  │ PRIMARY KEY              │
│  chapter_id      │ INTEGER  │ FOREIGN KEY → Progress   │
│  question_text   │ TEXT     │ The actual question      │
│  correct_answer  │ TEXT     │ The right answer         │
│  options         │ TEXT     │ Multiple choice options  │
│  difficulty      │ INTEGER  │ How hard? (1-5)          │
└────────────────────────────────────────────────────────┘
```

**Relationship:** Each question belongs to ONE chapter. One chapter can have MANY questions.

```
    Progress                    Questions
    ┌─────────┐                ┌─────────┐
    │chapter 1│◄───────────────│ Q1      │
    └─────────┘                │ Q2      │
                               │ Q3      │
    ┌─────────┐                └─────────┘
    │chapter 2│◄───────────────┌─────────┐
    └─────────┘                │ Q4      │
                               │ Q5      │
                               └─────────┘
```

**❓ Question 7:** This is called a "one-to-many" relationship. Can you explain in your own words what that means?

**❓ Question 8:** Why is `chapter_id` a Foreign Key in the Questions table, not a Primary Key?

---

### Model 3: StudyInformation

Stores the learning content (text, explanations) for each chapter.

**Purpose:** Hold the educational material users read to learn.

```
┌────────────────────────────────────────────────────────┐
│                   StudyInformation                      │
├────────────────────────────────────────────────────────┤
│  study_id        │ INTEGER  │ PRIMARY KEY              │
│  chapter_id      │ INTEGER  │ FOREIGN KEY → Progress   │
│  section_order   │ INTEGER  │ Order to display (1,2,3) │
│  title           │ TEXT     │ Section title            │
│  study_text      │ TEXT     │ The learning content     │
└────────────────────────────────────────────────────────┘
```

**❓ Question 9:** Why do we need `section_order`? What would happen if we didn't have it?

**❓ Question 10:** Could two different chapters have study sections with the same `section_order` number? Why or why not?

---

### Model 4: Assessment

Records the user's test/quiz results for each chapter.

**Purpose:** Track how well the user did on chapter tests.

```
┌────────────────────────────────────────────────────────┐
│                      Assessment                         │
├────────────────────────────────────────────────────────┤
│  assessment_id   │ INTEGER  │ PRIMARY KEY              │
│  chapter_id      │ INTEGER  │ FOREIGN KEY → Progress   │
│  score           │ INTEGER  │ Points earned            │
│  max_score       │ INTEGER  │ Maximum possible points  │
│  attempt_number  │ INTEGER  │ Which try? (1st, 2nd...) │
│  taken_at        │ DATETIME │ When was test taken?     │
└────────────────────────────────────────────────────────┘
```

**❓ Question 11:** Why do we store both `score` AND `max_score` instead of just a percentage?

**❓ Question 12:** Why might we want `attempt_number`? Should users be allowed to retake assessments?

---

## 🔗 Complete Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                        MoneyWise Academy Database                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │    Progress     │
                              ├─────────────────┤
                              │ chapter_id (PK) │
                              │ hardware_id     │
                              │ is_completed    │
                              │ started_at      │
                              │ completed_at    │
                              └────────┬────────┘
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           │                           │                           │
           │ FK                        │ FK                        │ FK
           ▼                           ▼                           ▼
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│     Questions       │    │  StudyInformation   │    │     Assessment      │
├─────────────────────┤    ├─────────────────────┤    ├─────────────────────┤
│ question_id (PK)    │    │ study_id (PK)       │    │ assessment_id (PK)  │
│ chapter_id (FK) ────┼─┐  │ chapter_id (FK) ────┼─┐  │ chapter_id (FK) ────┼─┐
│ question_text       │ │  │ section_order       │ │  │ score               │ │
│ correct_answer      │ │  │ title               │ │  │ max_score           │ │
│ options             │ │  │ study_text          │ │  │ attempt_number      │ │
│ difficulty          │ │  └─────────────────────┘ │  │ taken_at            │ │
└─────────────────────┘ │                          │  └─────────────────────┘ │
                        │                          │                          │
                        └──────────────────────────┴──────────────────────────┘
                                       │
                                       │
                            All FKs point to Progress.chapter_id


LEGEND:
  PK = Primary Key (unique identifier)
  FK = Foreign Key (reference to another table)
  ─► = "belongs to" / "references"
```

---

## ✅ Implementation Checklist

### Step 1: Setup (Do this first!)
- [ ] Open the file `src/data/database/models.py`
- [ ] Read the existing code and comments
- [ ] Make sure you understand what `Base = declarative_base()` does

### Step 2: Create Progress Model
- [ ] Define the Progress class
- [ ] Add all columns with correct data types
- [ ] Set up the primary key
- [ ] Add a `__tablename__` attribute

### Step 3: Create Questions Model
- [ ] Define the Questions class
- [ ] Add all columns with correct data types
- [ ] Set up primary key AND foreign key
- [ ] Define the relationship to Progress

### Step 4: Create StudyInformation Model
- [ ] Define the StudyInformation class
- [ ] Add all columns with correct data types
- [ ] Set up primary key AND foreign key
- [ ] Define the relationship to Progress

### Step 5: Create Assessment Model
- [ ] Define the Assessment class
- [ ] Add all columns with correct data types
- [ ] Set up primary key AND foreign key
- [ ] Define the relationship to Progress

### Step 6: Test Your Models
- [ ] Run the app to make sure there are no errors
- [ ] Check that the database tables are created

---

## 🔍 Research Tasks

Before you write any code, look up these things:

1. **SQLAlchemy Column Types** - What are the different data types you can use? (String, Integer, Boolean, DateTime, Text, etc.)

2. **SQLAlchemy ForeignKey** - How do you create a foreign key in SQLAlchemy?

3. **SQLAlchemy relationship()** - How do you define a relationship between models?

4. **`__tablename__`** - What is this and why do we need it?

---

## 💡 Hints (Only look if stuck!)

<details>
<summary>Hint 1: Basic Model Structure</summary>

Every model looks something like this:
```
class ModelName(Base):
    __tablename__ = 'table_name'
    
    column_name = Column(DataType, options...)
```
</details>

<details>
<summary>Hint 2: Primary Key</summary>

To make a column a primary key, you add `primary_key=True` to the Column definition.
</details>

<details>
<summary>Hint 3: Foreign Key</summary>

Foreign keys need TWO things:
1. The column with `ForeignKey('other_table.column_name')`
2. A `relationship()` to connect the models
</details>

---

## 📝 Final Questions (Answer after completing)

**❓ Question 13:** If you needed to find all questions for Chapter 3, how would the database know which questions belong to that chapter?

**❓ Question 14:** What would happen if you tried to add a Question with `chapter_id = 99` but there's no Chapter 99 in the Progress table?

**❓ Question 15:** Could you explain to someone else what a "one-to-many relationship" is? Write your explanation here:

_Your answer: _______________________________________________

**❓ Question 16:** Why do you think we use a database instead of just saving everything in a regular text file?

---

## 🎉 Bonus Challenges (Optional)

If you finish early and want an extra challenge:

1. **Add timestamps:** Add `created_at` and `updated_at` fields to all models
2. **Add validation:** What if someone tries to set difficulty to 10? How would you prevent that?
3. **Think ahead:** What other models might we need in the future? (Hint: achievements, badges, streaks?)

---

## 📚 Resources

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Python Database Tutorial](https://realpython.com/python-sqlite-sqlalchemy/)
- Ask your mentor if you get stuck!

---

**Remember:** It's okay to make mistakes! That's how we learn. Take your time, ask questions, and have fun! 🚀
