"""
Curated Quiz Question Bank for MIT Placement Preparation (Module 2)
Covers Aptitude, Coding, Technical Interview, and HR Interview.
Contains multiple-choice, coding-output, conceptual, numerical, and scenario-based questions.
"""

INITIAL_QUIZ_QUESTIONS = [
    # ==================== APTITUDE: QUANTITATIVE & LOGICAL ====================
    {
        "domain": "Aptitude",
        "topic": "Percentages & Ratios",
        "difficulty": "easy",
        "question_type": "numerical",
        "question_text": "A student's placement aptitude score increases by 20% in the second test and then decreases by 10% in the third test. What is the net percentage change in their score?",
        "code_snippet": None,
        "option_a": "10% increase",
        "option_b": "8% increase",
        "option_c": "12% increase",
        "option_d": "5% decrease",
        "correct_option": "B",
        "explanation": "Let initial score be 100. After 20% increase, score = 120. After 10% decrease on 120, decrease = 12, new score = 108. Net change = (108 - 100) = +8% increase."
    },
    {
        "domain": "Aptitude",
        "topic": "Time & Work",
        "difficulty": "medium",
        "question_type": "numerical",
        "question_text": "Developer A can build a module in 12 days, and Developer B can build the same module in 18 days. If they work together with Developer C, they complete it in 4 days. In how many days can C alone build the module?",
        "code_snippet": None,
        "option_a": "9 days",
        "option_b": "10 days",
        "option_c": "8 days",
        "option_d": "12 days",
        "correct_option": "A",
        "explanation": "Work rate: 1/A + 1/B + 1/C = 1/4. 1/12 + 1/18 + 1/C = 1/4. (3 + 2)/36 + 1/C = 1/4. 5/36 + 1/C = 9/36. 1/C = 4/36 = 1/9. Thus Developer C alone takes 9 days."
    },
    {
        "domain": "Aptitude",
        "topic": "Number Series",
        "difficulty": "easy",
        "question_type": "conceptual",
        "question_text": "Find the next number in the sequence: 4, 9, 25, 49, 121, ?",
        "code_snippet": None,
        "option_a": "144",
        "option_b": "169",
        "option_c": "196",
        "option_d": "225",
        "correct_option": "B",
        "explanation": "The terms are squares of consecutive prime numbers: 2^2=4, 3^2=9, 5^2=25, 7^2=49, 11^2=121. The next prime number is 13, so 13^2 = 169."
    },
    {
        "domain": "Aptitude",
        "topic": "Logical Deduction",
        "difficulty": "medium",
        "question_type": "conceptual",
        "question_text": "Statements: (1) All engineers are problem solvers. (2) Some problem solvers are leaders. Which conclusion logically follows?",
        "code_snippet": None,
        "option_a": "All engineers are leaders.",
        "option_b": "Some leaders are definitely engineers.",
        "option_c": "Some problem solvers are engineers.",
        "option_d": "No engineer can be a leader.",
        "correct_option": "C",
        "explanation": "Since all engineers are problem solvers, the set of engineers is contained within problem solvers. Therefore, some problem solvers are definitely engineers (conversion of statement 1)."
    },
    {
        "domain": "Aptitude",
        "topic": "Speed, Time & Distance",
        "difficulty": "hard",
        "question_type": "numerical",
        "question_text": "A train traveling at 72 km/h crosses a platform of length 250 meters in 25 seconds. What is the length of the train?",
        "code_snippet": None,
        "option_a": "200 meters",
        "option_b": "250 meters",
        "option_c": "300 meters",
        "option_d": "150 meters",
        "correct_option": "B",
        "explanation": "Speed = 72 * (5/18) = 20 m/s. Total distance crossed = Speed * Time = 20 * 25 = 500 meters. Total distance = Train Length + Platform Length = L + 250 = 500 => L = 250 meters."
    },
    {
        "domain": "Aptitude",
        "topic": "Data Interpretation",
        "difficulty": "medium",
        "question_type": "numerical",
        "question_text": "In a college placement drive, 160 students attended CSE interviews. If 25% were selected for Tech, 20% of remaining for Operations, and the rest were in reserve pool, how many are in the reserve pool?",
        "code_snippet": None,
        "option_a": "96",
        "option_b": "100",
        "option_c": "84",
        "option_d": "112",
        "correct_option": "A",
        "explanation": "Tech = 25% of 160 = 40. Remaining = 120. Operations = 20% of 120 = 24. Reserve pool = 120 - 24 = 96 students."
    },

    # ==================== CODING: DSA & FUNDAMENTALS ====================
    {
        "domain": "Coding",
        "topic": "Arrays & Strings",
        "difficulty": "easy",
        "question_type": "coding_output",
        "question_text": "What will be the output of the following Python snippet?",
        "code_snippet": "arr = [1, 2, 3, 4, 5]\narr[1:4] = [20, 30]\nprint(len(arr), arr)",
        "option_a": "4 [1, 20, 30, 5]",
        "option_b": "5 [1, 20, 30, 4, 5]",
        "option_c": "3 [1, 20, 30]",
        "option_d": "Error: slice assignment size mismatch",
        "correct_option": "A",
        "explanation": "In Python, slice assignment replaces the targeted slice (indices 1, 2, 3: [2, 3, 4]) with the given list [20, 30]. Length decreases from 5 to 4, resulting in [1, 20, 30, 5]."
    },
    {
        "domain": "Coding",
        "topic": "Time & Space Complexity",
        "difficulty": "medium",
        "question_type": "conceptual",
        "question_text": "What is the worst-case time complexity of searching for an element in an unbalanced Binary Search Tree (BST)?",
        "code_snippet": None,
        "option_a": "O(log N)",
        "option_b": "O(N log N)",
        "option_c": "O(N)",
        "option_d": "O(1)",
        "correct_option": "C",
        "explanation": "In an unbalanced (skewed) BST, each node has only one child, degenerating into a linked list. Hence, the worst-case search complexity is O(N)."
    },
    {
        "domain": "Coding",
        "topic": "Searching & Sorting",
        "difficulty": "medium",
        "question_type": "conceptual",
        "question_text": "Which sorting algorithm performs in O(N log N) time in worst, average, and best cases, but requires O(N) auxiliary space?",
        "code_snippet": None,
        "option_a": "Quick Sort",
        "option_b": "Merge Sort",
        "option_c": "Heap Sort",
        "option_d": "Insertion Sort",
        "correct_option": "B",
        "explanation": "Merge Sort consistently divides the array in half (log N levels) and merges them in O(N) time at each level, achieving O(N log N) in all cases, while requiring O(N) auxiliary array space for merging."
    },
    {
        "domain": "Coding",
        "topic": "Data Structures",
        "difficulty": "easy",
        "question_type": "conceptual",
        "question_text": "Which data structure is most appropriate for evaluating postfix arithmetic expressions or matching parentheses?",
        "code_snippet": None,
        "option_a": "Queue (FIFO)",
        "option_b": "Stack (LIFO)",
        "option_c": "Binary Tree",
        "option_d": "Hash Map",
        "correct_option": "B",
        "explanation": "A Stack works on Last-In, First-Out (LIFO), which makes it ideal for expression parsing, nested parenthesis verification, and call-stack management."
    },
    {
        "domain": "Coding",
        "topic": "Recursion & Dynamic Programming",
        "difficulty": "hard",
        "question_type": "coding_output",
        "question_text": "What will be printed when the recursive function is called with solve(3)?",
        "code_snippet": "def solve(n):\n    if n <= 0:\n        return 1\n    return solve(n - 1) + solve(n - 2)\nprint(solve(3))",
        "option_a": "3",
        "option_b": "4",
        "option_c": "5",
        "option_d": "6",
        "correct_option": "C",
        "explanation": "solve(0) = 1, solve(-1) = 1. solve(1) = solve(0) + solve(-1) = 1 + 1 = 2. solve(2) = solve(1) + solve(0) = 2 + 1 = 3. solve(3) = solve(2) + solve(1) = 3 + 2 = 5."
    },
    {
        "domain": "Coding",
        "topic": "Bit Manipulation",
        "difficulty": "medium",
        "question_type": "conceptual",
        "question_text": "What does the expression (x & (x - 1)) == 0 check for a positive integer x?",
        "code_snippet": None,
        "option_a": "Checks if x is an odd number",
        "option_b": "Checks if x is a prime number",
        "option_c": "Checks if x is a power of 2",
        "option_d": "Checks if x is divisible by 4",
        "correct_option": "C",
        "explanation": "Powers of 2 have exactly one bit set in binary (e.g., 8 is 1000). Subtracting 1 flips all trailing zeros and the set bit (7 is 0111). Bitwise AND yields 0, confirming x is a power of 2."
    },

    # ==================== TECHNICAL INTERVIEW: CS CORE ====================
    {
        "domain": "Technical Interview",
        "topic": "Object Oriented Programming (OOP)",
        "difficulty": "easy",
        "question_type": "conceptual",
        "question_text": "Which OOP concept refers to the ability of different classes to respond to the same method call in their own specific ways?",
        "code_snippet": None,
        "option_a": "Encapsulation",
        "option_b": "Polymorphism",
        "option_c": "Inheritance",
        "option_d": "Data Abstraction",
        "correct_option": "B",
        "explanation": "Polymorphism ('many forms') allows subclasses to override methods of a superclass or interface, providing customized behavior through dynamic method dispatch."
    },
    {
        "domain": "Technical Interview",
        "topic": "DBMS & SQL",
        "difficulty": "medium",
        "question_type": "conceptual",
        "question_text": "In relational databases, which ACID property guarantees that once a transaction completes, its changes survive even across a sudden system crash or power outage?",
        "code_snippet": None,
        "option_a": "Atomicity",
        "option_b": "Consistency",
        "option_c": "Isolation",
        "option_d": "Durability",
        "correct_option": "D",
        "explanation": "Durability guarantees that once a transaction has committed via write-ahead logging (WAL) and disk flush, its effects persist permanently even in the event of hardware or power failure."
    },
    {
        "domain": "Technical Interview",
        "topic": "DBMS & SQL",
        "difficulty": "medium",
        "question_type": "coding_output",
        "question_text": "Given table Employees(id, dept, salary), which query correctly finds the highest salary in each department?",
        "code_snippet": None,
        "option_a": "SELECT dept, MAX(salary) FROM Employees GROUP BY dept;",
        "option_b": "SELECT dept, salary FROM Employees WHERE salary = MAX(salary);",
        "option_c": "SELECT dept, MAX(salary) FROM Employees ORDER BY dept;",
        "option_d": "SELECT DISTINCT dept, salary FROM Employees WHERE MAX(salary);",
        "correct_option": "A",
        "explanation": "The GROUP BY dept clause groups records by department, and the aggregate function MAX(salary) calculates the maximum salary for each unique department group."
    },
    {
        "domain": "Technical Interview",
        "topic": "Operating Systems",
        "difficulty": "hard",
        "question_type": "conceptual",
        "question_text": "Which of the following conditions is NOT one of Coffman's four necessary conditions for a Deadlock to occur?",
        "code_snippet": None,
        "option_a": "Mutual Exclusion",
        "option_b": "Hold and Wait",
        "option_c": "Preemption allowed",
        "option_d": "Circular Wait",
        "correct_option": "C",
        "explanation": "The fourth condition is 'No Preemption' (resources cannot be forcibly taken). If preemption is allowed, deadlocks can be broken and prevented."
    },
    {
        "domain": "Technical Interview",
        "topic": "Computer Networks",
        "difficulty": "easy",
        "question_type": "conceptual",
        "question_text": "At which layer of the OSI model do TCP and UDP protocols operate?",
        "code_snippet": None,
        "option_a": "Network Layer (Layer 3)",
        "option_b": "Transport Layer (Layer 4)",
        "option_c": "Session Layer (Layer 5)",
        "option_d": "Data Link Layer (Layer 2)",
        "correct_option": "B",
        "explanation": "TCP and UDP are Transport Layer protocols responsible for end-to-end communication, port addressing, segmentation, and reliability."
    },
    {
        "domain": "Technical Interview",
        "topic": "Operating Systems",
        "difficulty": "medium",
        "question_type": "conceptual",
        "question_text": "What is the primary difference between a Process and a Thread?",
        "code_snippet": None,
        "option_a": "Threads have separate memory address spaces, while processes share memory.",
        "option_b": "Processes share address space, while threads require distinct page tables.",
        "option_c": "Threads within the same process share code, data, and heap, but each has its own stack and registers.",
        "option_d": "Threads can only run in user space, while processes always run in kernel space.",
        "correct_option": "C",
        "explanation": "A process has its own isolated address space. Threads (lightweight processes) of the same process share memory space (code, data, heap) while maintaining their own private stack and program counter."
    },

    # ==================== HR INTERVIEW: COMMUNICATION & SITUATIONAL ====================
    {
        "domain": "HR Interview",
        "topic": "STAR Method",
        "difficulty": "easy",
        "question_type": "hr_scenario",
        "question_text": "What does the STAR framework stand for when answering behavioral placement interview questions?",
        "code_snippet": None,
        "option_a": "Strategy, Timeline, Action, Review",
        "option_b": "Situation, Task, Action, Result",
        "option_c": "Skills, Technical depth, Aptitude, Readiness",
        "option_d": "Summary, Target, Assessment, Resolution",
        "correct_option": "B",
        "explanation": "STAR stands for Situation (context), Task (challenge/responsibility), Action (what you did specifically), and Result (quantifiable outcome of your actions)."
    },
    {
        "domain": "HR Interview",
        "topic": "Conflict Resolution",
        "difficulty": "medium",
        "question_type": "hr_scenario",
        "question_text": "During your final year college capstone project, a team member consistently misses deadlines, jeopardizing submission. What is the most professional response in an HR interview?",
        "code_snippet": None,
        "option_a": "Report them immediately to the HOD without speaking to them.",
        "option_b": "Do all their remaining work secretly and remove their name from the report.",
        "option_c": "Have a private one-on-one discussion to understand their obstacles, re-evaluate task breakdown, and set clear checkpoints before escalating.",
        "option_d": "Confront them in front of the entire class during lab hours.",
        "correct_option": "C",
        "explanation": "Professionalism requires empathy, proactive communication, and conflict resolution before escalation. Discussing privately to uncover blockers and redistributing deliverables demonstrates leadership."
    },
    {
        "domain": "HR Interview",
        "topic": "Self Introduction & Career Goals",
        "difficulty": "easy",
        "question_type": "hr_scenario",
        "question_text": "When an interviewer opens with 'Tell me about yourself', what should be your primary focus?",
        "code_snippet": None,
        "option_a": "Your complete family history, hometown landmarks, and childhood hobbies.",
        "option_b": "A structured pitch covering your academic background, core technical skills, key projects, and enthusiasm for this role.",
        "option_c": "Repeating every word already printed on your resume line by line.",
        "option_d": "Explaining why your college grades do not reflect your true intelligence.",
        "correct_option": "B",
        "explanation": "A high-impact self-introduction should follow the Present-Past-Future model: current degree and focus, key accomplishments and technical projects, and how your goals align with the hiring company."
    },
    {
        "domain": "HR Interview",
        "topic": "Strengths & Weaknesses",
        "difficulty": "medium",
        "question_type": "hr_scenario",
        "question_text": "When asked 'What is your biggest weakness?', what is the most effective approach?",
        "code_snippet": None,
        "option_a": "'I am an absolute perfectionist and I work too hard.'",
        "option_b": "'I have no technical weaknesses because I master everything quickly.'",
        "option_c": "State an honest non-fatal weakness, give a realistic example, and describe the proactive steps you are actively taking to improve.",
        "option_d": "Mention that you struggle with punctuality and waking up in the morning.",
        "correct_option": "C",
        "explanation": "Interviewers test self-awareness and growth mindset. Cliché answers like 'I work too hard' sound dishonest, while mentioning a real area (e.g., public speaking) alongside active remedial steps demonstrates maturity."
    },
    {
        "domain": "HR Interview",
        "topic": "Handling Ambiguity",
        "difficulty": "hard",
        "question_type": "hr_scenario",
        "question_text": "Your team lead gives you an open-ended assignment with minimal technical documentation. What is your best first step?",
        "code_snippet": None,
        "option_a": "Wait until detailed written documentation is provided by the manager.",
        "option_b": "Ask questions to clarify the high-level objective, do initial research, draft an action plan with assumptions, and validate it with the lead.",
        "option_c": "Start implementing whatever seems easiest without consulting anyone.",
        "option_d": "Request to be transferred to a different project with established manuals.",
        "correct_option": "B",
        "explanation": "Employers value initiative and structured problem-solving under ambiguity. Clarifying success metrics, researching independently, and validating proposed solutions before building avoids rework."
    }
]

def seed_quiz_questions(db_session, QuizQuestionModel):
    """Seed questions if table is empty"""
    existing_count = QuizQuestionModel.query.count()
    if existing_count == 0:
        for q in INITIAL_QUIZ_QUESTIONS:
            question = QuizQuestionModel(
                domain=q["domain"],
                topic=q["topic"],
                difficulty=q["difficulty"],
                question_type=q["question_type"],
                question_text=q["question_text"],
                code_snippet=q.get("code_snippet"),
                option_a=q["option_a"],
                option_b=q["option_b"],
                option_c=q["option_c"],
                option_d=q["option_d"],
                correct_option=q["correct_option"],
                explanation=q["explanation"]
            )
            db_session.add(question)
        db_session.commit()
        print(f"Successfully seeded {len(INITIAL_QUIZ_QUESTIONS)} quiz questions!")
    else:
        print(f"Quiz questions already seeded ({existing_count} existing).")
