# Educational Prompt Examples Library
*Template examples for AI Tutor to follow when creating educational tickets*

## Example Ticket: "Build a Counter Button App"
*Target: 12-18 year old African students learning programming basics*

---

## Installation Commands with Educational Explanations

### Command 1: Project Setup
```bash
Command: mkdir counter-app
Explanation: This creates a new folder called 'counter-app' where we'll put all our project files. Think of it like making a new folder for your school project - you want to keep everything organized in one place so you don't lose your work!
```

### Command 2: Navigate to Project
```bash
Command: cd counter-app
Explanation: This moves us into that folder, like opening the folder on your computer so we can work inside it. In programming, we always need to be "inside" our project folder to work on it.
```

### Command 3: Create HTML File
```bash
Command: touch index.html
Explanation: This creates a new HTML file - think of HTML like the skeleton of a webpage. Just like your body has bones that give it structure, HTML gives our app its basic structure.
```

---

## Educational Cursor Prompts (Sequential Building)

### Cursor Prompt 1: Understanding Variables with Counter
```
I'm a 12-year-old in Kenya learning to code for the first time. I want to build a simple counter app that could help me count things in my daily life, like how many bottles of water my family needs each day.

Help me create the basic HTML structure and explain what a variable is. Create an HTML file with:
1. A title that says "Water Bottle Counter"
2. A display showing the current count
3. A variable in JavaScript to store the count number

Please generate most of the code but leave the variable name empty (like let _____ = 0) so I can fill it in myself. 

Explain to me like I'm 12:
- What is a variable and why do we need it?
- How is a variable like a container or box?
- Why would counting be useful in solving real problems in African communities?
- What should I name my variable and why?

Also tell me what I should research to learn more about variables.
```

### Cursor Prompt 2: Building Interactive Buttons
```
I'm continuing my water bottle counter app. Now I understand variables - they're like labeled boxes that store information! 

Help me add a button that people can click. I want to understand why we sometimes use button libraries instead of making buttons from scratch.

Please:
1. Show me how to create a simple HTML button
2. Explain why programmers sometimes use libraries (like Bootstrap) for buttons
3. Add basic styling to make the button look nice
4. Leave the button text empty so I can write what it should say

Generate most of the code but leave these gaps for me to fill:
- The button text (what should it say?)
- The button color in CSS

Explain to me like I'm 12:
- What is a library in programming and why do we use them?
- How is using a library like using pre-made LEGO blocks?
- Why do we care about making our apps look nice for users?
- What are some popular button libraries I could explore?

Connect this to real life: How do good-looking, easy-to-use apps help people in African communities access important services?
```

### Cursor Prompt 3: Creating Functions and Logic
```
I'm building my water bottle counter and now I have a variable and a button! Next, I need to make the button actually DO something when clicked.

Help me create a function that increases the counter when the button is clicked. I want to understand how functions work and how they connect to user actions.

Please:
1. Create a JavaScript function that adds 1 to the counter
2. Connect the button click to this function
3. Update the display to show the new count
4. Leave some gaps in the logic for me to complete

Generate the code structure but leave these for me to fill:
- The function name (what should I call it?)
- The math operation inside the function (counter = counter + ___)
- The event listener type (button.addEventListener('____', functionName))

Explain to me like I'm 12:
- What is a function and why do we use them?
- How is a function like a recipe or instructions?
- What does "event listener" mean and how does it work?
- Why do we break code into small functions instead of writing everything together?

Real-world connection: How do interactive apps help people in Africa track important things like water usage, medicine doses, or school attendance? Give me some examples of counting apps that could help my community.

Research topics for me to explore:
- Different types of events (click, hover, etc.)
- Function parameters and return values
- How to organize code with multiple functions
```

### Cursor Prompt 4: Connecting Everything Together
```
I'm finishing my water bottle counter app! I have variables, a button, and a function. Now I need to put it all together and make sure everything works as one complete app.

Help me:
1. Connect all the pieces (HTML, CSS, JavaScript) properly
2. Add error handling (what if someone clicks too fast?)
3. Make the app responsive so it works on phones
4. Add a reset button to start counting over

Please generate the final integration code but leave these important gaps:
- The reset function logic (how to set counter back to zero?)
- CSS media queries for mobile devices
- Comments explaining each section

Explain to me like I'm 12:
- Why do we need to test our app on different devices?
- What is "error handling" and why is it important?
- How do we make sure our code is easy for other people to understand?
- What makes an app "professional" vs just a school project?

Real-world impact: Explain how this simple counter app demonstrates important programming concepts used in apps that help African communities with:
- Healthcare (counting pills, tracking symptoms)
- Education (tracking attendance, homework completion)
- Business (inventory management, sales tracking)
- Agriculture (crop counting, livestock management)

Final challenge questions for me to think about:
1. How would you modify this to count different things?
2. What would you add to make it useful for a local business?
3. How could you share this app with friends who don't have good internet?
```

---

## Test Commands for Verification

### Command 1: Test HTML Structure
```bash
Command: open index.html
Explanation: This opens your HTML file in a web browser so you can see your app! It's like checking your homework - you want to see if what you built actually works the way you expected.
```

### Command 2: Check JavaScript Console
```bash
Command: Press F12 in browser, click Console tab
Explanation: This opens the developer tools where you can see if there are any errors in your code. Think of it like a report card for your code - it tells you what's working and what needs fixing.
```

### Command 3: Test on Mobile
```bash
Command: Press F12, click device icon, select "iPhone"
Explanation: This shows you how your app looks on a phone. Since many people in Africa use phones more than computers, we always need to make sure our apps work well on small screens!
```

---

## Key Educational Patterns to Follow

### 1. Age-Appropriate Explanations
- Always use analogies (variables = boxes, functions = recipes)
- Connect to familiar objects and experiences
- Break complex concepts into simple parts

### 2. African Context Integration
- Reference local challenges and opportunities
- Show how technology solves real community problems
- Use relevant examples (water, education, agriculture)

### 3. Progressive Building
- Each prompt builds on the previous one
- Leave meaningful gaps for student completion
- Provide clear research directions

### 4. Real-World Connections
- Always explain why the concept matters
- Show professional applications
- Connect to community impact

### 5. Learning Reinforcement
- Include questions to test understanding
- Provide research topics for deeper learning
- Challenge students to think beyond the exercise 