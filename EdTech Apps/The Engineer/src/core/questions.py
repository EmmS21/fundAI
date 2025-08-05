ENGINEERING_QUESTIONS = [
    # Problem Solving & Debugging Section (20 questions)
    {
        'id': 1,
        'section': 'Problem Solving & Debugging',
        'question': 'Your phone suddenly won\'t charge. What do you try first?',
        'options': [
            'Buy a new phone immediately',
            'Try a different charging cable',
            'Check if the charging port has lint or dirt',
            'Try plugging into a different wall outlet',
            'Ask someone else to try charging their phone with your cable'
        ],
        'correct': [1, 2, 3, 4],
        'explanation': 'Good debugging tests each part of the system systematically.',
        'difficulty': 'beginner'
    },
    {
        'id': 2,
        'section': 'Problem Solving & Debugging',
        'question': 'You\'re baking cookies and they come out burnt on the bottom but raw on top. What went wrong?',
        'options': [
            'The oven temperature was too high',
            'The rack was too close to the bottom heating element',
            'You opened the oven door too many times',
            'The cookie sheet was too dark/black',
            'The recipe was completely wrong'
        ],
        'correct': [0, 1, 3],
        'explanation': 'Understanding heat distribution helps debug baking problems.',
        'difficulty': 'beginner'
    },
    {
        'id': 3,
        'section': 'Problem Solving & Debugging',
        'question': 'Your bike chain keeps falling off. How do you figure out why?',
        'options': [
            'Check if the chain is the right size',
            'See if the derailleur is bent',
            'Look for worn or damaged chain links',
            'Just put it back on and hope it stays',
            'Check if the gears are properly aligned'
        ],
        'correct': [0, 1, 2, 4],
        'explanation': 'Mechanical problems require checking all related components.',
        'difficulty': 'beginner'
    },
    {
        'id': 4,
        'section': 'Problem Solving & Debugging',
        'question': 'Your gaming controller randomly disconnects. What\'s your debugging strategy?',
        'options': [
            'Check the battery level',
            'Try connecting it to a different device',
            'Look for interference from other wireless devices',
            'Reset the controller to factory settings',
            'Throw it away and buy a new one'
        ],
        'correct': [0, 1, 2, 3],
        'explanation': 'Wireless problems often have multiple possible causes to check.',
        'difficulty': 'beginner'
    },
    {
        'id': 5,
        'section': 'Problem Solving & Debugging',
        'question': 'You follow a YouTube tutorial but your result looks completely different. What do you do?',
        'options': [
            'Watch the video again and pause at each step',
            'Check the comments to see if others had the same problem',
            'Compare your materials/tools to what they used',
            'Give up because you\'re bad at following instructions',
            'Try to figure out which step went wrong'
        ],
        'correct': [0, 1, 2, 4],
        'explanation': 'Debugging tutorials requires systematic comparison and community help.',
        'difficulty': 'intermediate'
    },
    {
        'id': 6,
        'section': 'Problem Solving & Debugging',
        'question': 'Your WiFi works everywhere except your bedroom. How do you solve this?',
        'options': [
            'Move the router closer to your bedroom',
            'Check if there are walls or objects blocking the signal',
            'Use a WiFi extender',
            'Change your WiFi password',
            'Test the signal strength in different spots'
        ],
        'correct': [0, 1, 2, 4],
        'explanation': 'WiFi problems often relate to distance and physical obstacles.',
        'difficulty': 'intermediate'
    },
    {
        'id': 7,
        'section': 'Problem Solving & Debugging',
        'question': 'Your 3D print keeps failing halfway through. What could be wrong?',
        'options': [
            'The printer is running out of filament',
            'The bed temperature is wrong',
            'The print is too complex for your skill level',
            'There\'s a clog in the nozzle',
            'The file is corrupted'
        ],
        'correct': [0, 1, 3, 4],
        'explanation': '3D printing failures have multiple technical causes to investigate.',
        'difficulty': 'advanced'
    },
    {
        'id': 8,
        'section': 'Problem Solving & Debugging',
        'question': 'Your car won\'t start in the morning. What\'s your troubleshooting process?',
        'options': [
            'Check if the headlights were left on',
            'Try jumping the battery',
            'Call a mechanic immediately',
            'Check if there\'s gas in the tank',
            'Listen to what sounds the car makes when you try to start it'
        ],
        'correct': [0, 1, 3, 4],
        'explanation': 'Car troubleshooting starts with checking obvious causes and gathering information.',
        'difficulty': 'intermediate'
    },
    {
        'id': 9,
        'section': 'Problem Solving & Debugging',
        'question': 'Your streaming video keeps buffering. How do you fix it?',
        'options': [
            'Check your internet speed',
            'Close other apps using the internet',
            'Try a lower video quality',
            'Restart your router',
            'Blame the streaming service'
        ],
        'correct': [0, 1, 2, 3],
        'explanation': 'Streaming problems usually relate to bandwidth and network issues.',
        'difficulty': 'beginner'
    },
    {
        'id': 10,
        'section': 'Problem Solving & Debugging',
        'question': 'Your homemade slime is too sticky. How do you debug this?',
        'options': [
            'Add more activator (contact solution/borax)',
            'Mix it longer',
            'Start over with a new recipe',
            'Add more glue',
            'Let it sit for a while before mixing more'
        ],
        'correct': [0, 1, 4],
        'explanation': 'Chemical reactions like slime-making follow predictable rules for troubleshooting.',
        'difficulty': 'beginner'
    },
    {
        'id': 11,
        'section': 'Problem Solving & Debugging',
        'question': 'Your computer is running really slowly. What do you check?',
        'options': [
            'How much storage space is left',
            'How many programs are running at once',
            'If there are any viruses',
            'How old the computer is',
            'If it needs a software update'
        ],
        'correct': [0, 1, 2, 4],
        'explanation': 'Computer performance issues have multiple common causes to investigate.',
        'difficulty': 'intermediate'
    },
    {
        'id': 12,
        'section': 'Problem Solving & Debugging',
        'question': 'Your robot/drone won\'t respond to the remote. What\'s wrong?',
        'options': [
            'The batteries in the remote are dead',
            'The robot needs to be paired with the remote again',
            'You\'re too far away from the robot',
            'The robot\'s battery is dead',
            'The remote is broken'
        ],
        'correct': [0, 1, 2, 3],
        'explanation': 'Remote control problems involve checking both devices and their connection.',
        'difficulty': 'beginner'
    },
    {
        'id': 13,
        'section': 'Problem Solving & Debugging',
        'question': 'Your headphones only work in one ear. How do you troubleshoot?',
        'options': [
            'Try them with a different device',
            'Check if the audio balance is set correctly',
            'Wiggle the cable to see if it\'s a loose connection',
            'Clean the headphone jack',
            'Buy new headphones immediately'
        ],
        'correct': [0, 1, 2, 3],
        'explanation': 'Audio problems can be hardware or software related.',
        'difficulty': 'beginner'
    },
    {
        'id': 14,
        'section': 'Problem Solving & Debugging',
        'question': 'Your plant is dying despite watering it. What might be wrong?',
        'options': [
            'You\'re giving it too much water',
            'It\'s not getting enough sunlight',
            'The soil doesn\'t drain well',
            'You\'re not watering it enough',
            'It needs plant food/fertilizer'
        ],
        'correct': [0, 1, 2, 4],
        'explanation': 'Plant care problems require understanding multiple environmental factors.',
        'difficulty': 'intermediate'
    },
    {
        'id': 15,
        'section': 'Problem Solving & Debugging',
        'question': 'Your skateboard/scooter suddenly feels wobbly. What do you check?',
        'options': [
            'Are the wheels tight?',
            'Are the bearings worn out?',
            'Is the deck cracked?',
            'Are you riding on a smooth surface?',
            'Is your stance different than usual?'
        ],
        'correct': [0, 1, 2],
        'explanation': 'Mechanical wobbling usually indicates loose or worn parts.',
        'difficulty': 'beginner'
    },
    {
        'id': 16,
        'section': 'Problem Solving & Debugging',
        'question': 'Your homemade volcano won\'t erupt properly. What went wrong?',
        'options': [
            'Wrong ratio of baking soda to vinegar',
            'The baking soda is too old',
            'The volcano hole is too narrow',
            'You need to add food coloring',
            'The vinegar is too cold'
        ],
        'correct': [0, 1, 2],
        'explanation': 'Chemical reactions depend on proper ratios and fresh ingredients.',
        'difficulty': 'beginner'
    },
    {
        'id': 17,
        'section': 'Problem Solving & Debugging',
        'question': 'Your paper airplane doesn\'t fly straight. How do you fix it?',
        'options': [
            'Check if the wings are even',
            'Make sure the folds are crisp',
            'Adjust the weight distribution',
            'Try throwing it harder',
            'Use different paper'
        ],
        'correct': [0, 1, 2],
        'explanation': 'Aerodynamics problems usually involve balance and symmetry.',
        'difficulty': 'beginner'
    },
    {
        'id': 18,
        'section': 'Problem Solving & Debugging',
        'question': 'Your microwave heats food unevenly. What\'s happening?',
        'options': [
            'The turntable isn\'t working',
            'The food is too thick',
            'The microwave power is too high',
            'You need to stir/flip the food halfway through',
            'The microwave is broken'
        ],
        'correct': [0, 1, 3],
        'explanation': 'Microwave heating patterns depend on movement and food thickness.',
        'difficulty': 'intermediate'
    },
    {
        'id': 19,
        'section': 'Problem Solving & Debugging',
        'question': 'Your DIY circuit/LED project isn\'t lighting up. What do you check?',
        'options': [
            'Is the battery connected properly?',
            'Are all the wires touching where they should?',
            'Is the LED connected the right way (+ and -)?',
            'Is the battery dead?',
            'Is the LED burned out?'
        ],
        'correct': [0, 1, 2, 3, 4],
        'explanation': 'Electrical circuits require checking all connections and components.',
        'difficulty': 'intermediate'
    },
    {
        'id': 20,
        'section': 'Problem Solving & Debugging',
        'question': 'Your homemade app/game crashes when you tap a button. What\'s your approach?',
        'options': [
            'Try tapping other buttons to see if they work',
            'Check if it happens every time or just sometimes',
            'Look at what that button is supposed to do',
            'Try restarting the app',
            'Ask someone else to try it'
        ],
        'correct': [0, 1, 2, 3, 4],
        'explanation': 'Software debugging requires systematic testing and reproducing the problem.',
        'difficulty': 'advanced'
    },

    # Planning & Collaboration Section (15 questions)
    {
        'id': 21,
        'section': 'Planning & Collaboration',
        'question': 'You and friends are planning a surprise party. How do you organize who does what?',
        'options': [
            'Create a shared list where everyone can see their tasks',
            'Have one person in charge of assigning everything',
            'Let everyone just figure it out as they go',
            'Use a group chat to coordinate',
            'Meet regularly to check progress'
        ],
        'correct': [0, 3, 4],
        'explanation': 'Good project coordination requires clear communication and tracking.',
        'difficulty': 'intermediate'
    },
    {
        'id': 22,
        'section': 'Planning & Collaboration',
        'question': 'You\'re working on a group presentation. Everyone keeps changing the same slides. What\'s the solution?',
        'options': [
            'Take turns editing - only one person at a time',
            'Each person works on different sections',
            'Use a system that shows who changed what',
            'Have one person do all the editing',
            'Copy the presentation before making major changes'
        ],
        'correct': [1, 2, 4],
        'explanation': 'Collaboration conflicts need clear ownership and version control.',
        'difficulty': 'intermediate'
    },
    {
        'id': 23,
        'section': 'Planning & Collaboration',
        'question': 'You spent hours on a school project, then accidentally deleted it. How could you have prevented this?',
        'options': [
            'Save multiple copies with different names',
            'Use cloud storage that automatically saves',
            'Email yourself a copy',
            'Be more careful when deleting files',
            'Save it on a USB drive too'
        ],
        'correct': [0, 1, 2, 4],
        'explanation': 'Good backup strategies use multiple methods and locations.',
        'difficulty': 'beginner'
    },
    {
        'id': 24,
        'section': 'Planning & Collaboration',
        'question': 'You\'re building a treehouse. What should you plan first?',
        'options': [
            'What tools you\'ll need',
            'How big it should be and where to put it',
            'What color to paint it',
            'How much weight it needs to support',
            'Whether the tree is strong enough'
        ],
        'correct': [1, 3, 4],
        'explanation': 'Construction planning starts with requirements and constraints.',
        'difficulty': 'intermediate'
    },
    {
        'id': 25,
        'section': 'Planning & Collaboration',
        'question': 'Your band wants to write a song together. How do you organize the process?',
        'options': [
            'Everyone writes their own version, then combine them',
            'Work on different parts (verses, chorus, bridge) separately',
            'Jam together and record ideas',
            'Have one person write everything',
            'Use voice memos to save ideas before they\'re forgotten'
        ],
        'correct': [1, 2, 4],
        'explanation': 'Creative collaboration needs structure while preserving spontaneity.',
        'difficulty': 'intermediate'
    },
    {
        'id': 26,
        'section': 'Planning & Collaboration',
        'question': 'You\'re organizing a school fundraiser. How do you track progress?',
        'options': [
            'Keep a list of who signed up to help',
            'Track how much money you\'ve raised so far',
            'Note what tasks are done and what\'s left',
            'Just check everything the day before',
            'Have regular team meetings to update progress'
        ],
        'correct': [0, 1, 2, 4],
        'explanation': 'Event management requires tracking multiple metrics and regular check-ins.',
        'difficulty': 'intermediate'
    },
    {
        'id': 27,
        'section': 'Planning & Collaboration',
        'question': 'You\'re making a stop-motion video with friends. How do you coordinate?',
        'options': [
            'Plan out the story scene by scene first',
            'Assign roles (camera person, animator, editor)',
            'Just start filming and figure it out',
            'Create a shared folder for all the video files',
            'Decide on the style and look before starting'
        ],
        'correct': [0, 1, 3, 4],
        'explanation': 'Video projects need pre-planning and clear role assignments.',
        'difficulty': 'advanced'
    },
    {
        'id': 28,
        'section': 'Planning & Collaboration',
        'question': 'Your gaming team keeps losing because you\'re not coordinated. What helps?',
        'options': [
            'Use voice chat to communicate',
            'Assign specific roles to each player',
            'Practice strategies together',
            'Let the best player make all decisions',
            'Review what went wrong after each game'
        ],
        'correct': [0, 1, 2, 4],
        'explanation': 'Team coordination requires communication, roles, and continuous improvement.',
        'difficulty': 'intermediate'
    },
    {
        'id': 29,
        'section': 'Planning & Collaboration',
        'question': 'You\'re planning a camping trip with friends. What do you organize first?',
        'options': [
            'Who\'s bringing what equipment',
            'What food everyone likes',
            'How to split the costs',
            'What activities you want to do',
            'Transportation to the campsite'
        ],
        'correct': [0, 2, 4],
        'explanation': 'Trip planning prioritizes logistics and cost-sharing.',
        'difficulty': 'beginner'
    },
    {
        'id': 30,
        'section': 'Planning & Collaboration',
        'question': 'Your class is doing a group research project. How do you divide the work?',
        'options': [
            'Each person researches a different aspect',
            'Everyone researches everything, then compare',
            'Assign based on people\'s interests and strengths',
            'Let the smartest person do most of the work',
            'Create a timeline for when each part is due'
        ],
        'correct': [0, 2, 4],
        'explanation': 'Effective teamwork leverages individual strengths with clear deadlines.',
        'difficulty': 'intermediate'
    },
    {
        'id': 31,
        'section': 'Planning & Collaboration',
        'question': 'You\'re creating a comic book with friends. How do you manage different ideas?',
        'options': [
            'Vote on which ideas to include',
            'Combine everyone\'s ideas into one story',
            'Take turns - each person\'s idea gets used somewhere',
            'The person who draws best decides everything',
            'Keep a list of ideas for future comics'
        ],
        'correct': [0, 2, 4],
        'explanation': 'Creative collaboration requires democratic decision-making and idea management.',
        'difficulty': 'intermediate'
    },
    {
        'id': 32,
        'section': 'Planning & Collaboration',
        'question': 'You\'re building a Minecraft world together. How do you avoid conflicts?',
        'options': [
            'Give each person their own area to build in',
            'Plan the overall design before anyone starts building',
            'Use a shared chest system for materials',
            'Let anyone build anywhere',
            'Have building rules everyone agrees on'
        ],
        'correct': [0, 1, 2, 4],
        'explanation': 'Collaborative building needs territories, planning, and agreed-upon rules.',
        'difficulty': 'beginner'
    },
    {
        'id': 33,
        'section': 'Planning & Collaboration',
        'question': 'Your robotics team has different ideas for your robot design. How do you decide?',
        'options': [
            'Build a quick prototype of each idea to test',
            'List pros and cons of each approach',
            'Go with whatever the team captain wants',
            'Try to combine the best parts of each idea',
            'Vote, but make sure everyone understands each option'
        ],
        'correct': [0, 1, 3, 4],
        'explanation': 'Engineering decisions benefit from testing, analysis, and informed consensus.',
        'difficulty': 'advanced'
    },
    {
        'id': 34,
        'section': 'Planning & Collaboration',
        'question': 'You\'re organizing a neighborhood cleanup. How do you coordinate volunteers?',
        'options': [
            'Create a sign-up sheet with specific time slots',
            'Assign different areas to different groups',
            'Provide all the cleaning supplies yourself',
            'Let people just show up whenever',
            'Have team leaders for each area'
        ],
        'correct': [0, 1, 4],
        'explanation': 'Volunteer coordination requires structure and clear leadership.',
        'difficulty': 'intermediate'
    },
    {
        'id': 35,
        'section': 'Planning & Collaboration',
        'question': 'Your friend group wants to learn skateboarding together. How do you organize practice?',
        'options': [
            'Meet at the same time and place regularly',
            'Help each other learn new tricks',
            'Film each other to see what needs improvement',
            'Everyone practices alone, then shows off',
            'Start with basics before trying advanced tricks'
        ],
        'correct': [0, 1, 2, 4],
        'explanation': 'Skill development benefits from regular practice, peer support, and progression.',
        'difficulty': 'beginner'
    },

    # Data & Systems Thinking Section (15 questions)
    {
        'id': 36,
        'section': 'Data & Systems Thinking',
        'question': 'You\'re creating a contact list for your class. What information is most important?',
        'options': [
            'Name and phone number',
            'Name, phone, email, and birthday',
            'Name, phone, email, and emergency contact',
            'Everything you know about each person',
            'Just names - you can ask for other info later'
        ],
        'correct': [0, 2],
        'explanation': 'Good data design includes essential information without being overwhelming.',
        'difficulty': 'beginner'
    },
    {
        'id': 37,
        'section': 'Data & Systems Thinking',
        'question': 'You\'re organizing your music library. What\'s the best way to categorize songs?',
        'options': [
            'By artist and album',
            'By genre and mood',
            'By when you added them',
            'All songs in one big list',
            'By how much you like them'
        ],
        'correct': [0, 1, 4],
        'explanation': 'Organization systems should reflect how you actually search for and use items.',
        'difficulty': 'beginner'
    },
    {
        'id': 38,
        'section': 'Data & Systems Thinking',
        'question': 'TikTok shows you specific videos on your "For You" page. How does it decide what to show?',
        'options': [
            'Videos you\'ve liked or shared before',
            'Videos similar to ones you\'ve watched completely',
            'Random popular videos',
            'Videos from people you follow',
            'Videos that match your interests and viewing patterns'
        ],
        'correct': [0, 1, 4],
        'explanation': 'Recommendation systems analyze user behavior patterns to predict preferences.',
        'difficulty': 'intermediate'
    },
    {
        'id': 39,
        'section': 'Data & Systems Thinking',
        'question': 'You\'re designing a simple library checkout system. What do you need to track?',
        'options': [
            'Which books are available vs checked out',
            'Who has which book and when it\'s due',
            'How popular each book is',
            'The detailed plot of every book',
            'Late fees owed by each person'
        ],
        'correct': [0, 1, 4],
        'explanation': 'Systems design focuses on operational needs rather than nice-to-have information.',
        'difficulty': 'intermediate'
    },
    {
        'id': 40,
        'section': 'Data & Systems Thinking',
        'question': 'You\'re creating a pet care app. What\'s the most important information to track?',
        'options': [
            'Feeding schedule and last meal time',
            'Vet appointments and medical history',
            'Pet\'s favorite toys and treats',
            'Daily mood and behavior notes',
            'Emergency contact information'
        ],
        'correct': [0, 1, 4],
        'explanation': 'Critical systems prioritize health, safety, and routine care information.',
        'difficulty': 'intermediate'
    },
    {
        'id': 41,
        'section': 'Data & Systems Thinking',
        'question': 'When you order something online, what needs to happen in the system?',
        'options': [
            'Check if the item is in stock',
            'Process your payment',
            'Create a shipping label',
            'Send you a confirmation email',
            'All of these things need to happen'
        ],
        'correct': [4],
        'explanation': 'E-commerce systems require multiple coordinated processes to complete an order.',
        'difficulty': 'advanced'
    },
    {
        'id': 42,
        'section': 'Data & Systems Thinking',
        'question': 'You\'re organizing a tournament bracket. What information system do you need?',
        'options': [
            'Player names and skill levels',
            'Match results and winners',
            'Tournament schedule and locations',
            'Player favorite snacks',
            'Running score/ranking throughout the tournament'
        ],
        'correct': [0, 1, 2, 4],
        'explanation': 'Tournament systems track participants, results, and progression through rounds.',
        'difficulty': 'intermediate'
    },
    {
        'id': 43,
        'section': 'Data & Systems Thinking',
        'question': 'Your school wants to track student attendance. What\'s the most efficient system?',
        'options': [
            'Teachers mark who\'s present in each class',
            'Students check in themselves when they arrive',
            'Have someone at the entrance count everyone',
            'Don\'t track it - just trust students show up',
            'Use student ID cards to automatically track entry'
        ],
        'correct': [0, 4],
        'explanation': 'Attendance systems balance accuracy, efficiency, and ease of use.',
        'difficulty': 'intermediate'
    },
    {
        'id': 44,
        'section': 'Data & Systems Thinking',
        'question': 'You\'re creating a chore tracking system for your family. What should it include?',
        'options': [
            'List of chores and who\'s assigned to each',
            'When each chore was last completed',
            'How long each chore typically takes',
            'Rewards for completing chores',
            'History of who did what chores'
        ],
        'correct': [0, 1, 3],
        'explanation': 'Household management systems track assignments, completion, and incentives.',
        'difficulty': 'beginner'
    },
    {
        'id': 45,
        'section': 'Data & Systems Thinking',
        'question': 'YouTube recommends videos after you watch one. What information does it use?',
        'options': [
            'Videos you\'ve watched before',
            'Videos your friends have liked',
            'How long you watched each video',
            'What you searched for recently',
            'Random suggestions'
        ],
        'correct': [0, 2, 3],
        'explanation': 'Video recommendation systems analyze viewing patterns and search behavior.',
        'difficulty': 'intermediate'
    },
    {
        'id': 46,
        'section': 'Data & Systems Thinking',
        'question': 'You\'re designing a simple weather app. What data is most useful to users?',
        'options': [
            'Current temperature and conditions',
            'Hourly forecast for today',
            '7-day forecast',
            'Historical weather data from 10 years ago',
            'Severe weather alerts'
        ],
        'correct': [0, 1, 2, 4],
        'explanation': 'User-focused design prioritizes actionable, timely information.',
        'difficulty': 'beginner'
    },
    {
        'id': 47,
        'section': 'Data & Systems Thinking',
        'question': 'Your gaming clan wants to track member progress. What should you monitor?',
        'options': [
            'Each player\'s current level and skills',
            'How often each player is online',
            'Team achievements and goals',
            'Individual player\'s favorite game modes',
            'Progress toward clan objectives'
        ],
        'correct': [0, 1, 2, 4],
        'explanation': 'Gaming systems track individual progress and collective achievements.',
        'difficulty': 'intermediate'
    },
    {
        'id': 48,
        'section': 'Data & Systems Thinking',
        'question': 'You\'re organizing a food delivery system for your neighborhood. What do you need to track?',
        'options': [
            'Who ordered what food',
            'Delivery addresses and phone numbers',
            'Payment status for each order',
            'Delivery driver locations',
            'Customer favorite cuisines'
        ],
        'correct': [0, 1, 2, 3],
        'explanation': 'Delivery systems coordinate orders, payments, locations, and logistics.',
        'difficulty': 'advanced'
    },
    {
        'id': 49,
        'section': 'Data & Systems Thinking',
        'question': 'Instagram shows you posts in a specific order. Why not just show the newest posts first?',
        'options': [
            'You might miss important posts from close friends',
            'The algorithm shows you what you\'re most likely to engage with',
            'It keeps you scrolling longer',
            'Newer posts aren\'t always more interesting',
            'Random order is more fun'
        ],
        'correct': [0, 1, 3],
        'explanation': 'Social media algorithms optimize for user engagement and relevance.',
        'difficulty': 'advanced'
    },
    {
        'id': 50,
        'section': 'Data & Systems Thinking',
        'question': 'You\'re creating a homework tracking app. What features matter most?',
        'options': [
            'List of assignments with due dates',
            'Reminders before things are due',
            'Progress tracking (not started/in progress/done)',
            'Integration with your calendar',
            'Detailed time logs of how long you worked'
        ],
        'correct': [0, 1, 2, 3],
        'explanation': 'Productivity systems focus on deadlines, reminders, and status tracking.',
        'difficulty': 'intermediate'
    }
]

QUESTION_SECTIONS = {
    'Problem Solving & Debugging': {
        'description': 'How do you approach problems when things go wrong?',
        'icon': '🔍'
    },
    'Planning & Collaboration': {
        'description': 'How do you organize work and collaborate with others?', 
        'icon': '🗂️'
    },
    'Data & Systems Thinking': {
        'description': 'How do you think about organizing information and building systems?',
        'icon': '💾'
    }
}

def get_questions_by_section(section):
    return [q for q in ENGINEERING_QUESTIONS if q['section'] == section]

def get_random_questions(count=15):
    import random
    
    # Ensure we get roughly equal distribution across sections
    debugging_questions = [q for q in ENGINEERING_QUESTIONS if q['section'] == 'Problem Solving & Debugging']
    planning_questions = [q for q in ENGINEERING_QUESTIONS if q['section'] == 'Planning & Collaboration']
    data_questions = [q for q in ENGINEERING_QUESTIONS if q['section'] == 'Data & Systems Thinking']
    
    # Select roughly 1/3 from each section
    selected = []
    selected.extend(random.sample(debugging_questions, min(7, len(debugging_questions))))
    selected.extend(random.sample(planning_questions, min(4, len(planning_questions))))
    selected.extend(random.sample(data_questions, min(4, len(data_questions))))
    
    # If we need more questions, randomly select from remaining
    if len(selected) < count:
        remaining = [q for q in ENGINEERING_QUESTIONS if q not in selected]
        selected.extend(random.sample(remaining, min(count - len(selected), len(remaining))))
    
    return random.sample(selected, min(count, len(selected))) 