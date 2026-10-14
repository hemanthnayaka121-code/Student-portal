"""
AI Mock Interview Engine for MIT Placement Preparation (Module 2)
Manages multi-turn interviews, question generation, answer evaluation,
follow-up questions, and final comprehensive report generation.
Integrates with external LLM (Gemini API) with an intelligent expert-rubric fallback.
"""

import os
import json
import random
from datetime import datetime
import requests

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# Comprehensive Question Banks for each Interview Type and Difficulty
# Formatted in clear, natural conversational English like a real placement sir / mam
INTERVIEW_QUESTION_POOLS = {
    "Coding": {
        "Easy": [
            {
                "question": "Let's start with a coding question. How would you reverse an array in-place without using extra memory? And what would be the time complexity?",
                "expected": "Use two-pointer technique: swap arr[left] and arr[right], then increment left and decrement right until left >= right. Time complexity is O(N/2) = O(N), space complexity is O(1) in-place.",
                "domain": "Coding - Arrays & Pointers"
            },
            {
                "question": "Can you explain how you would check if a string is a palindrome? What kind of cases like spaces or uppercase and lowercase letters would you consider?",
                "expected": "Normalize the string by stripping non-alphanumeric chars and converting to lower case. Check using two pointers from start and end. Edge cases: empty string, single character string, strings with only spaces/punctuation.",
                "domain": "Coding - Strings"
            },
            {
                "question": "In your own words, what is the main difference between an array and a linked list? When would you choose one over the other in a project?",
                "expected": "Arrays provide O(1) random access but O(N) insertion/deletion and fixed size in static memory. LinkedLists provide dynamic sizing and O(1) insertion/deletion at known nodes, but O(N) access and pointer memory overhead.",
                "domain": "Coding - Data Structures"
            },
            {
                "question": "How would you find the second largest number in an unsorted list in just a single pass without sorting?",
                "expected": "Maintain two variables: largest = -inf, second = -inf. Traverse array: if x > largest, second = largest, largest = x; elif x > second and x != largest, second = x. Time O(N), Space O(1).",
                "domain": "Coding - Logic & Traversal"
            },
            {
                "question": "Can you explain what hashing is, and what happens when two different keys end up in the same bucket in a hash table?",
                "expected": "Hashing maps keys to table indices using a hash function. Chaining stores colliding elements in a linked list or balanced tree at the bucket. Open addressing searches for next open slot using linear, quadratic probing or double hashing.",
                "domain": "Coding - Hashing"
            }
        ],
        "Medium": [
            {
                "question": "Suppose you are given daily stock prices in a list. How would you find the best single day to buy and sell to make the maximum profit in one pass?",
                "expected": "Track min_price seen so far and max_profit. Iterate through array: min_price = min(min_price, price); max_profit = max(max_profit, price - min_price). Return max_profit. Time O(N), Space O(1).",
                "domain": "Coding - Dynamic Programming / Greedy"
            },
            {
                "question": "If you are given a singly linked list, how do you check if there is a cycle or loop in it without using extra memory?",
                "expected": "Floyd's Cycle-Finding Algorithm (Tortoise and Hare). Slow pointer moves 1 step, fast pointer moves 2 steps. If fast == slow, cycle exists. If fast reaches NULL, no cycle. Time O(N), Space O(1).",
                "domain": "Coding - Linked Lists"
            },
            {
                "question": "Can you explain what the sliding window technique is? When would you use it instead of checking all possible subarrays?",
                "expected": "Sliding window maintains a window [left, right] that expands and contracts based on conditions, avoiding redundant recalculations. Example: finding the longest substring without repeating characters using a frequency map.",
                "domain": "Coding - Algorithms"
            },
            {
                "question": "How does binary search work, and why is it so much faster than linear search? Can you also tell me what the time complexity is?",
                "expected": "Binary search divides sorted space by comparing middle. In languages like C++/Java with fixed 32-bit signed ints, low + high can overflow if both are large. Fix: `low + (high - low) // 2`. Time complexity O(log N).",
                "domain": "Coding - Binary Search"
            },
            {
                "question": "How would you compare Quick Sort and Merge Sort? Which one do you prefer to use and why?",
                "expected": "Merge sort is stable and guarantees O(N log N) worst-case, preferred for linked lists due to sequential access. Quick sort is unstable, in-place O(1) auxiliary space, with O(N log N) average case and better cache locality for arrays.",
                "domain": "Coding - Sorting"
            }
        ],
        "Hard": [
            {
                "question": "How would you design a simple LRU cache where both get and put operations happen in constant O(1) time?",
                "expected": "Combine a Hash Map with a Doubly Linked List. The Hash Map stores key -> Node pointer for O(1) lookup. Doubly Linked List maintains access order with most recent at head, least recent at tail for O(1) removal and re-insertion.",
                "domain": "Coding - System Design & DSA"
            },
            {
                "question": "Can you explain the main difference between Dijkstra's algorithm and Bellman-Ford for finding the shortest path in a graph?",
                "expected": "Dijkstra uses a Min-Heap/Priority Queue with greedy selection, O((V + E) log V), but fails on negative weight edges. Bellman-Ford relaxes all edges V-1 times, handles negative weights, and detects negative cycles in O(V * E) time.",
                "domain": "Coding - Graph Algorithms"
            }
        ]
    },
    "Technical": {
        "Easy": [
            {
                "question": "Can you explain the four main pillars of Object-Oriented Programming using simple real-world examples?",
                "expected": "Encapsulation (bundling data and methods, e.g., capsule/car dashboard), Abstraction (hiding implementation details, e.g., driving without seeing internal engine mechanics), Inheritance (code reuse, e.g., vehicle -> car), Polymorphism (multiple forms, e.g., sound() for Dog vs Cat).",
                "domain": "Technical - OOP"
            },
            {
                "question": "In databases, what is the difference between a Primary Key, a Foreign Key, and a Unique Key?",
                "expected": "Primary Key uniquely identifies each row, cannot be NULL, only one per table. Unique Key enforces uniqueness but allows one NULL value. Foreign Key refers to a Primary Key in another table, enforcing referential integrity.",
                "domain": "Technical - DBMS"
            },
            {
                "question": "Can you tell me what happens in an operating system when you run a program, and what is the difference between user mode and kernel mode?",
                "expected": "OS allocates PCB (Process Control Block), address space (text, data, heap, stack). User mode restricts direct hardware access for safety; kernel mode has full privileged CPU access. System calls transition CPU from user to kernel mode via software interrupts.",
                "domain": "Technical - OS"
            },
            {
                "question": "Can you explain how the three-way handshake works in TCP before two computers start sending data?",
                "expected": "SYN (Client to Server with Seq#), SYN-ACK (Server to Client with Ack# and Server Seq#), ACK (Client to Server with Ack#). Ensures both sender and receiver agree on initial sequence numbers and socket readiness before transmission.",
                "domain": "Technical - Computer Networks"
            },
            {
                "question": "What is database normalization, and why is it important when we design database tables?",
                "expected": "Normalization eliminates data redundancy and update anomalies. 1NF: atomic values, no repeating groups. 2NF: in 1NF + no partial dependency on composite primary key. 3NF: in 2NF + no transitive dependency on non-prime attributes.",
                "domain": "Technical - DBMS"
            }
        ],
        "Medium": [
            {
                "question": "Could you explain what ACID properties are in database systems, and why they are especially important in banking applications?",
                "expected": "Atomicity (all or nothing), Consistency (preserves database integrity constraints), Isolation (concurrent transactions execute independently without dirty reads), Durability (committed changes survive system crashes). Crucial for money transfer: debit and credit must both succeed or rollback.",
                "domain": "Technical - DBMS"
            },
            {
                "question": "What is virtual memory and paging in an operating system, and what does it mean when a system starts thrashing?",
                "expected": "Virtual memory gives processes an illusion of contiguous large memory using disk backing. Paging divides memory into fixed-size frames and pages. Thrashing occurs when high page fault frequency causes CPU to spend more time swapping pages than executing instructions.",
                "domain": "Technical - OS"
            },
            {
                "question": "What is the key difference between TCP and UDP? In what kind of applications would you definitely choose UDP?",
                "expected": "TCP is connection-oriented, reliable, ordered, with flow and congestion control. UDP is connectionless, lightweight, unordered without retransmission overhead. Use cases: live video streaming (Zoom, YouTube Live), online gaming, DNS lookups, VoIP.",
                "domain": "Technical - Networks"
            },
            {
                "question": "What are database indexes, and how do clustered and non-clustered indexes differ?",
                "expected": "Indexes are B-tree data structures that accelerate queries. Clustered Index determines physical storage order of data on disk (only 1 per table, typically PK). Non-Clustered Index is a separate structure with pointers back to data rows (multiple per table).",
                "domain": "Technical - DBMS"
            },
            {
                "question": "Can you explain what a REST API is? What are the main HTTP methods like GET and POST, and how do they differ?",
                "expected": "REST is an architectural style based on stateless client-server resources. GET, PUT, DELETE are idempotent (multiple identical calls produce same server state). POST is non-idempotent (creates a new resource each invocation).",
                "domain": "Technical - Web Architecture"
            }
        ],
        "Hard": [
            {
                "question": "How does an operating system deal with deadlocks? Can you briefly describe deadlock prevention and avoidance?",
                "expected": "Prevention eliminates one of 4 Coffman conditions. Avoidance checks safe states using Banker's Algorithm before resource allocation. Detection runs wait-for graph cycle detection. Recovery terminates deadlocked processes or preempts resources.",
                "domain": "Technical - Operating Systems"
            },
            {
                "question": "In databases, what are transaction isolation levels, and why do we need them when many users access the database at the same time?",
                "expected": "Read Uncommitted allows dirty reads. Read Committed prevents dirty reads using write locks. Repeatable Read prevents non-repeatable reads using shared read locks. Serializable prevents phantom reads using range locks or multi-version concurrency control (MVCC).",
                "domain": "Technical - DBMS Architecture"
            }
        ]
    },
    "HR": {
        "Easy": [
            {
                "question": "Welcome! To begin with, could you please introduce yourself and tell me what made you choose engineering at MIT Mysore?",
                "expected": "Structured introduction: Current branch/semester at MIT, core technical strengths, key project highlights, problem-solving passion, and excitement for this company's domain.",
                "domain": "HR - Self Introduction"
            },
            {
                "question": "Why do you want to join our company specifically, and what kind of work excites you the most?",
                "expected": "Demonstrate company research: mention specific products, engineering culture, recent innovations, and how the student's skills align with the company's tech stack and mission.",
                "domain": "HR - Company Fit"
            },
            {
                "question": "Where do you see yourself in the next two to three years in your engineering career?",
                "expected": "Short-term (1-2 yrs): Master the tech stack, deliver impactful features, learn from senior engineers. Long-term (3-5 yrs): Take ownership of system modules, lead technical initiatives, mentor juniors.",
                "domain": "HR - Career Goals"
            },
            {
                "question": "What would you say is your biggest strength, and what is one area you are currently trying to improve?",
                "expected": "Clear strength backed by project evidence (e.g., perseverance in debugging complex issues). Honest constructive weakness (e.g., public speaking or initial delegation) with active remedial steps.",
                "domain": "HR - Self Awareness"
            },
            {
                "question": "Are you comfortable relocating to different cities or learning new programming languages as project needs change?",
                "expected": "Enthusiastic flexibility and adaptability. Express eagerness to work in modern environments and learn new technologies quickly as a continuous learner.",
                "domain": "HR - Adaptability"
            }
        ],
        "Medium": [
            {
                "question": "Can you tell me about a time in college when you had a disagreement with a project teammate? How did you both talk it through and resolve it?",
                "expected": "STAR framework: Context of disagreement, understanding teammate's viewpoint, evaluating pros and cons objectively with data or prototypes, reaching consensus, and delivering project successfully on schedule.",
                "domain": "HR - Conflict Resolution"
            },
            {
                "question": "Tell me about a time when a project or deadline did not go as planned. What happened, and what did you learn from it?",
                "expected": "Accountability without blaming others, root-cause analysis (e.g., underestimated scope or lacked early testing), corrective action taken, and permanent habits developed (e.g., early sprint milestones, buffer planning).",
                "domain": "HR - Resilience & Learning"
            },
            {
                "question": "How do you manage your time and stress when exams, lab submissions, and placement prep all happen at the same time?",
                "expected": "Time management strategies: prioritization (Eisenhower Matrix), breaking tasks into manageable chunks, disciplined daily routines, avoiding procrastination, and maintaining calm focus.",
                "domain": "HR - Pressure Management"
            },
            {
                "question": "Can you give an example of a new tool or technology you had to learn quickly on your own? How did you go about learning it?",
                "expected": "Specific example: tool name, how they leveraged official documentation, video lessons, and hands-on mini-prototyping, how quickly they achieved proficiency, and the outcome achieved.",
                "domain": "HR - Fast Learner"
            }
        ],
        "Hard": [
            {
                "question": "Suppose you are assigned to an existing project with very little documentation and a short deadline. How would you approach understanding the code and delivering results?",
                "expected": "Breakdown into systematic exploration: set up local reproducible environment, write integration tests to understand existing behavior, trace logs, consult subject matter experts, scope MVP, communicate risks transparently to manager.",
                "domain": "HR - Ambiguity & Ownership"
            }
        ]
    },
    "Aptitude": {
        "Easy": [
            {
                "question": "Let's do a quick aptitude problem. If a person sells an item for 2,400 rupees making a 20 percent profit, what was the cost price, and what would the profit percentage be if it sold for 2,600?",
                "expected": "CP = 2400 / 1.20 = Rs. 2,000. If sold at 2600, Profit = 600. Profit % = (600 / 2000) * 100 = 30%.",
                "domain": "Aptitude - Profit & Loss"
            },
            {
                "question": "Here is a time and work question. If 6 men or 8 women can finish a task in 28 days, how many days will it take for 9 men and 12 women working together?",
                "expected": "6 men = 8 women => 1 man = 4/3 women. 9 men = 12 women. Total workers = 12 + 12 = 24 women. M1*D1 = M2*D2 => 8 * 28 = 24 * D2 => D2 = (8 * 28) / 24 = 28 / 3 = 9.33 days.",
                "domain": "Aptitude - Work & Time"
            },
            {
                "question": "Can you explain how you would calculate the angle between the hour hand and the minute hand of a clock at 3:30?",
                "expected": "Angle formula: |30*H - 5.5*M| = |30*3 - 5.5*30| = |90 - 165| = 75 degrees.",
                "domain": "Aptitude - Clocks & Angles"
            }
        ],
        "Medium": [
            {
                "question": "Two cars start from two points 300 kilometers apart and travel toward each other at 60 and 90 kilometers per hour. When and where will they meet?",
                "expected": "Relative speed = 60 + 90 = 150 km/h. Time to meet = Distance / Relative Speed = 300 / 150 = 2 hours. Distance from A = 60 * 2 = 120 km.",
                "domain": "Aptitude - Relative Speed"
            },
            {
                "question": "A container holds 40 liters of milk. If 4 liters are removed and replaced with water, and this is repeated twice more, how much pure milk is left?",
                "expected": "Remaining milk = Initial * (1 - x/C)^n = 40 * (1 - 4/40)^3 = 40 * (0.9)^3 = 40 * 0.729 = 29.16 liters.",
                "domain": "Aptitude - Mixtures & Alligations"
            }
        ],
        "Hard": [
            {
                "question": "In how many ways can the letters of the word 'CAMPUS' be arranged such that the vowels always occupy the odd positions?",
                "expected": "Letters = 6 (Vowels: A, U [2], Consonants: C, M, P, S [4]). Odd positions: 1, 3, 5 (3 slots). Vowels in 3 slots = 3P2 = 6 ways. Remaining 4 slots for 4 consonants = 4! = 24 ways. Total = 6 * 24 = 144 ways.",
                "domain": "Aptitude - Permutations"
            }
        ]
    }
}

def generate_interview_questions(interview_type, difficulty, count=5, student=None):
    """
    Selects or generates tailored interview questions matching interview type, difficulty,
    and student's department/skills.
    """
    # Map mixed / resume types
    if interview_type == "Mixed":
        # Mix of Coding (40%), Technical (30%), HR (20%), Aptitude (10%)
        all_types = ["Coding", "Technical", "HR", "Aptitude"]
    elif interview_type in ["Resume & Project", "Resume and project-based interview"]:
        all_types = ["Technical", "Coding", "HR"]
    else:
        # Standard types: Coding, Technical, HR, Aptitude
        all_types = [interview_type if interview_type in INTERVIEW_QUESTION_POOLS else "Technical"]

    selected_pool = []
    diff_key = difficulty if difficulty in ["Easy", "Medium", "Hard"] else "Medium"

    for t in all_types:
        pool = INTERVIEW_QUESTION_POOLS.get(t, {}).get(diff_key, [])
        if not pool:
            pool = INTERVIEW_QUESTION_POOLS.get(t, {}).get("Medium", [])
        selected_pool.extend(pool)

    # Randomly shuffle and select requested count
    random.shuffle(selected_pool)
    final_questions = selected_pool[:count]
    
    # If pool is smaller than count, cycle
    while len(final_questions) < count and selected_pool:
        final_questions.append(random.choice(selected_pool))

    # Format list
    result = []
    for idx, q in enumerate(final_questions, start=1):
        # Personalize if student provided
        q_text = q['question']
        if student and idx == 1 and interview_type in ["HR", "Mixed", "Resume & Project"]:
            q_text = f"Welcome {student.name}. You are pursuing {student.department.name} with skills in {student.skills}. {q_text}"
        
        result.append({
            'question_number': idx,
            'question_text': q_text,
            'expected_answer_points': q['expected'],
            'domain': q['domain']
        })
    return result

def evaluate_answer_with_ai(question_text, student_answer, expected_points, interview_type="Technical", difficulty="Medium"):
    """
    Evaluates student answer using Gemini API if configured, or uses intelligent
    campus placement heuristic rubric engine.
    Returns:
        dict: {score (0-100), feedback, strengths, weaknesses, follow_up_question}
    """
    answer_text = (student_answer or "").strip()
    if not answer_text:
        return {
            'score': 0.0,
            'feedback': "No answer was recorded. In an interview, silence gives zero marks. Even an attempt to structure an approach or ask clarifying questions is better than no response.",
            'strengths': "None identified.",
            'weaknesses': "Did not attempt the question.",
            'follow_up_question': "Would you like to try explaining what initial intuition or approach comes to mind for this problem?"
        }

    # 1. Try Gemini API if key is present
    gemini_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if gemini_key:
        try:
            prompt = f"""You are a senior technical and HR placement interviewer evaluating an engineering candidate at MIT Mysore.
Evaluate this student response against the interview question and rubric.

Question: {question_text}
Expected Key Points: {expected_points}
Interview Type: {interview_type}
Difficulty: {difficulty}
Student's Answer: {answer_text}

Provide output in strict valid JSON format with keys:
- "score": number between 0 and 100
- "feedback": 2-3 sentences of constructive feedback
- "strengths": 1 sentence highlight of what was good
- "weaknesses": 1 sentence highlight of missed points or flaws
- "follow_up_question": a relevant technical or conceptual follow-up question
Only return the JSON object, nothing else."""

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            resp = requests.post(url, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                text_content = data['candidates'][0]['content']['parts'][0]['text']
                # Clean JSON markdown if present
                clean_json = text_content.strip()
                if clean_json.startswith('```json'):
                    clean_json = clean_json[7:]
                if clean_json.endswith('```'):
                    clean_json = clean_json[:-3]
                parsed = json.loads(clean_json.strip())
                return {
                    'score': float(parsed.get('score', 75.0)),
                    'feedback': parsed.get('feedback', 'Good structured response.'),
                    'strengths': parsed.get('strengths', 'Clear conceptual attempt.'),
                    'weaknesses': parsed.get('weaknesses', 'Can be more concise.'),
                    'follow_up_question': parsed.get('follow_up_question', 'Can you discuss the time complexity?')
                }
        except Exception as e:
            # Fall through to rubric engine
            pass

    # 2. Expert Campus Placement Heuristic Rubric Engine
    # Word count, keyword matching from expected points, technical structure
    words = answer_text.split()
    word_count = len(words)
    
    expected_words = set([w.lower().strip(".,()[]:;") for w in expected_points.split() if len(w) > 3])
    student_words = set([w.lower().strip(".,()[]:;") for w in words if len(w) > 3])
    
    matches = expected_words.intersection(student_words)
    match_ratio = len(matches) / max(1, len(expected_words))

    # Base score derived from key concepts matched and completeness
    if word_count < 10:
        base_score = 45.0 + (match_ratio * 30.0)
        feedback = "Good start, but your answer was a bit brief. In an interview, try to explain your thought process and give a quick example."
        strengths = "You made a quick attempt."
        weaknesses = "Could add more details and explanation."
        follow_up = "Could you tell me how you would approach this step-by-step or in actual code?"
    elif match_ratio >= 0.35:
        base_score = min(96.0, 78.0 + (match_ratio * 30.0))
        matched_str = f"especially regarding {', '.join(list(matches)[:3])}" if matches else ""
        feedback = f"Great explanation! You explained the concept clearly {matched_str}. That's exactly what interviewers look for."
        strengths = "Clear, confident explanation with accurate technical points."
        weaknesses = "You can also mention time and space complexity to make it even more complete."
        follow_up = "That makes sense! How would your solution handle a very large input, like a million records?"
    elif word_count >= 20:
        base_score = 68.0 + (match_ratio * 25.0)
        feedback = "Nice effort! You communicated your thoughts well. Just remember to mention the core technical terms directly so the panel knows you have a strong foundation."
        strengths = "Good conversational flow and clear logic."
        weaknesses = f"Could specifically touch upon {list(expected_words)[:2]}." if expected_words else "Can be slightly more specific."
        follow_up = "Can you give a quick real-world example of where this is used?"
    else:
        base_score = 58.0
        feedback = "Good attempt! You have the right direction in mind. Try to walk through the steps clearly one by one."
        strengths = "Good attempt to answer."
        weaknesses = "Can be a bit more specific on the core steps."
        follow_up = "Can you walk through a simple example of this?"

    score = round(min(100.0, max(25.0, base_score)), 1)
    
    return {
        'score': score,
        'feedback': feedback,
        'strengths': strengths,
        'weaknesses': weaknesses,
        'follow_up_question': follow_up
    }

def generate_comprehensive_interview_report(session):
    """
    Synthesizes the complete interview record into a structured post-interview report.
    """
    qnas = session.qna_records
    if not qnas:
        return {}

    scores = [q.score for q in qnas if q.score is not None]
    overall_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    # Question details
    q_reports = []
    strengths_list = []
    weaknesses_list = []

    for q in qnas:
        q_reports.append({
            'question_number': q.question_number,
            'question_text': q.question_text,
            'student_answer': q.student_answer or "No answer provided.",
            'expected_points': q.expected_answer_points,
            'score': q.score or 0.0,
            'feedback': q.feedback,
            'audio_mode': q.audio_mode,
            'follow_up': q.follow_up_question
        })
        if q.score and q.score >= 75:
            strengths_list.append(f"Q{q.question_number}: Strong understanding demonstrated.")
        elif q.score and q.score < 65:
            weaknesses_list.append(f"Q{q.question_number}: Needs deeper practice on core concepts.")

    # Communication & Explanation Feedback
    audio_count = sum(1 for q in qnas if q.audio_mode)
    if audio_count > len(qnas) / 2:
        comm_feedback = "Demonstrated confident voice interaction using microphone. Good pacing and professional tone."
    else:
        comm_feedback = "Primarily text-based responses. Practicing in voice mode is highly recommended to build speaking confidence for in-person campus rounds."

    # Next recommendations
    if overall_score >= 80:
        next_diff = "Hard" if session.difficulty != "Hard" else "Hard (Company Specific)"
        recommendation_text = "Excellent interview performance! You demonstrated technical mastery and structured thinking. Advance to higher difficulty and timed rounds."
    elif overall_score >= 65:
        next_diff = "Medium"
        recommendation_text = "Good baseline performance. Review the missed points in the questions above, attempt a 5-question targeted quiz, and retry a Medium mock session."
    else:
        next_diff = "Easy"
        recommendation_text = "Foundational concepts require review. Watch the recommended video lessons in your weakest domain and practice with diagnostic quizzes before your next interview."

    report = {
        'session_id': session.id,
        'interview_type': session.interview_type,
        'difficulty': session.difficulty,
        'question_count': session.question_count,
        'overall_score': overall_score,
        'questions_count_answered': len(scores),
        'questions_detail': q_reports,
        'strengths': strengths_list if strengths_list else ["Good willingness to attempt interview questions."],
        'weaknesses': weaknesses_list if weaknesses_list else ["Minor edge case handling can be polished."],
        'communication_feedback': comm_feedback,
        'next_recommended_difficulty': next_diff,
        'recommendation_text': recommendation_text,
        'suggested_next_action': "Attempt Practice Quiz in " + session.interview_type
    }

    return report
