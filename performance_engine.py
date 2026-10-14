"""
Performance Analysis Engine for MIT Placement Preparation (Module 2)
Analyzes student performance across Aptitude, Coding, Technical Interview, and HR Interview.
Identifies strengths, weaknesses, benchmarks, and generates actionable learning recommendations.
"""

from datetime import datetime

BENCHMARK_SCORE = 70.0 # Benchmark threshold percentage

DOMAIN_TOPICS = {
    "Aptitude": [
        "Quantitative Aptitude & Percentages",
        "Logical Reasoning & Syllogisms",
        "Number Series & Pattern Recognition",
        "Data Interpretation & Analysis",
        "Speed, Time & Distance Shortcuts"
    ],
    "Coding": [
        "Arrays & Strings Manipulation",
        "Searching & Sorting Algorithms",
        "Data Structures (Stack, Queue, Trees)",
        "Time & Space Complexity (Big-O)",
        "Object Oriented Programming & C/Java/Python"
    ],
    "Technical Interview": [
        "OOP Concepts & Design Patterns",
        "DBMS, Normalization & SQL Queries",
        "Operating Systems (Processes, Threads, Deadlocks)",
        "Computer Networks (OSI, TCP/IP, Protocols)",
        "Resume Projects & System Architecture"
    ],
    "HR Interview": [
        "Self-Introduction Pitch (Present-Past-Future)",
        "STAR Method for Behavioral Questions",
        "Strengths & Constructive Weaknesses Framing",
        "Teamwork, Leadership & Conflict Resolution",
        "Company Research & Career Goals Alignment"
    ]
}

def analyze_student_performance(student):
    """
    Computes a comprehensive performance evaluation for a given student object.
    Distinguishes unrecorded assessments from genuine zero scores.
    Returns:
        dict with domain scores, statuses, readiness score, strongest/weakest domain,
        detailed gap analysis, action plans, and recommended YouTube search queries.
    """
    perf = student.performance
    activities = student.activities or []
    quiz_attempts = student.quiz_attempts or []
    mock_sessions = student.interview_sessions or []

    # 1. Domain Raw Marks Extraction
    # Official recorded marks:
    # Aptitude: 0-100 scale
    # Coding: average of (coding_c_score, coding_java_score, coding_dsa_score)
    # Technical: technical_interview_score
    # HR: hr_score (or based on hr_status if unrecorded)
    
    domains_eval = {}

    # --- APTITUDE ---
    if perf and perf.aptitude_score is not None:
        apt_score = round(perf.aptitude_score, 1)
        apt_assessed = True
    else:
        apt_score = None
        apt_assessed = False

    # Check recent quiz attempts in Aptitude to augment data
    apt_quizzes = [q for q in quiz_attempts if q.domain == 'Aptitude']
    apt_quiz_avg = round(sum(q.score_pct for q in apt_quizzes) / len(apt_quizzes), 1) if apt_quizzes else None

    # Effective score considering quizzes if official is not available
    effective_apt = apt_score if apt_assessed else apt_quiz_avg

    domains_eval['Aptitude'] = {
        'domain': 'Aptitude',
        'assessed': apt_assessed or (apt_quiz_avg is not None),
        'official_score': apt_score,
        'quiz_score': apt_quiz_avg,
        'effective_score': effective_apt,
        'max_score': 100,
        'benchmark': BENCHMARK_SCORE,
        'subtopics': DOMAIN_TOPICS['Aptitude']
    }

    # --- CODING ---
    if perf and (perf.coding_c_score is not None or perf.coding_java_score is not None or perf.coding_dsa_score is not None):
        c_sc = perf.coding_c_score or 0.0
        j_sc = perf.coding_java_score or 0.0
        d_sc = perf.coding_dsa_score or 0.0
        coding_score = round((c_sc + j_sc + d_sc) / 3.0, 1)
        coding_assessed = True
    else:
        coding_score = None
        coding_assessed = False

    coding_quizzes = [q for q in quiz_attempts if q.domain == 'Coding']
    coding_quiz_avg = round(sum(q.score_pct for q in coding_quizzes) / len(coding_quizzes), 1) if coding_quizzes else None
    effective_coding = coding_score if coding_assessed else coding_quiz_avg

    domains_eval['Coding'] = {
        'domain': 'Coding',
        'assessed': coding_assessed or (coding_quiz_avg is not None),
        'official_score': coding_score,
        'coding_breakdown': {
            'C': perf.coding_c_score if perf else None,
            'Java': perf.coding_java_score if perf else None,
            'DSA': perf.coding_dsa_score if perf else None
        },
        'quiz_score': coding_quiz_avg,
        'effective_score': effective_coding,
        'max_score': 100,
        'benchmark': BENCHMARK_SCORE,
        'subtopics': DOMAIN_TOPICS['Coding']
    }

    # --- TECHNICAL INTERVIEW ---
    if perf and perf.technical_interview_score is not None and perf.technical_interview_score > 0:
        tech_score = round(perf.technical_interview_score, 1)
        tech_assessed = True
    else:
        tech_score = None
        tech_assessed = False

    tech_quizzes = [q for q in quiz_attempts if q.domain == 'Technical Interview']
    tech_quiz_avg = round(sum(q.score_pct for q in tech_quizzes) / len(tech_quizzes), 1) if tech_quizzes else None
    effective_tech = tech_score if tech_assessed else tech_quiz_avg

    domains_eval['Technical Interview'] = {
        'domain': 'Technical Interview',
        'assessed': tech_assessed or (tech_quiz_avg is not None),
        'official_score': tech_score,
        'quiz_score': tech_quiz_avg,
        'effective_score': effective_tech,
        'max_score': 100,
        'benchmark': BENCHMARK_SCORE,
        'subtopics': DOMAIN_TOPICS['Technical Interview']
    }

    # --- HR INTERVIEW ---
    if perf and perf.hr_score is not None and perf.hr_score > 0:
        hr_score = round(perf.hr_score, 1)
        hr_assessed = True
    elif perf and perf.hr_status is not None:
        hr_score = 85.0 if perf.hr_status else 45.0
        hr_assessed = True
    else:
        hr_score = None
        hr_assessed = False

    hr_quizzes = [q for q in quiz_attempts if q.domain == 'HR Interview']
    hr_quiz_avg = round(sum(q.score_pct for q in hr_quizzes) / len(hr_quizzes), 1) if hr_quizzes else None
    effective_hr = hr_score if hr_assessed else hr_quiz_avg

    domains_eval['HR Interview'] = {
        'domain': 'HR Interview',
        'assessed': hr_assessed or (hr_quiz_avg is not None),
        'official_score': hr_score,
        'quiz_score': hr_quiz_avg,
        'effective_score': effective_hr,
        'max_score': 100,
        'benchmark': BENCHMARK_SCORE,
        'subtopics': DOMAIN_TOPICS['HR Interview']
    }

    # 2. Detailed Gap Analysis & Recommendations for Each Domain
    evaluated_list = []
    for d_name, d_info in domains_eval.items():
        score = d_info['effective_score']
        assessed = d_info['assessed']
        
        if not assessed or score is None:
            status = "Not Assessed"
            badge_class = "badge-neutral"
            reason = f"No diagnostic or official marks have been recorded yet for {d_name}."
            action_plan = f"Attempt a diagnostic placement quiz in {d_name} to assess your current baseline proficiency."
            rec_topic = d_info['subtopics'][0]
            rec_query = f"{d_name} campus placement preparation tutorial"
        elif score >= BENCHMARK_SCORE:
            status = "Strength"
            badge_class = "badge-pass"
            reason = f"Your recorded {d_name} performance ({score}%) exceeds the college placement benchmark of {BENCHMARK_SCORE}%."
            action_plan = f"Maintain your advantage by solving advanced problems and practicing timed mock interview rounds in {d_name}."
            rec_topic = d_info['subtopics'][-1]
            rec_query = f"advanced {rec_topic} interview questions"
        else:
            status = "Weakness"
            badge_class = "badge-fail"
            deficit = round(BENCHMARK_SCORE - score, 1)
            reason = f"Your score of {score}% is {deficit}% below the required campus placement benchmark ({BENCHMARK_SCORE}%)."
            action_plan = f"Focus on core concepts starting with {d_info['subtopics'][0]}, watch the recommended video lesson, then attempt a practice quiz."
            rec_topic = d_info['subtopics'][0]
            rec_query = f"{rec_topic} tutorial for college placement"

        d_info['status'] = status
        d_info['badge_class'] = badge_class
        d_info['reason'] = reason
        d_info['action_plan'] = action_plan
        d_info['recommended_topic'] = rec_topic
        d_info['recommended_query'] = rec_query
        evaluated_list.append(d_info)

    # 3. Identify Strongest and Weakest Domain
    assessed_domains = [d for d in evaluated_list if d['assessed'] and d['effective_score'] is not None]
    if assessed_domains:
        sorted_domains = sorted(assessed_domains, key=lambda x: x['effective_score'])
        weakest_domain = sorted_domains[0]
        strongest_domain = sorted_domains[-1]
    else:
        weakest_domain = evaluated_list[0]
        strongest_domain = evaluated_list[1]

    # 4. Overall Placement Readiness Score (0 - 100)
    # Weights: Aptitude (25%), Coding (35%), Tech (25%), HR (15%)
    weights = {'Aptitude': 0.25, 'Coding': 0.35, 'Technical Interview': 0.25, 'HR Interview': 0.15}
    total_weighted = 0.0
    weight_sum = 0.0

    for d_name, d_info in domains_eval.items():
        w = weights.get(d_name, 0.25)
        if d_info['effective_score'] is not None:
            total_weighted += d_info['effective_score'] * w
            weight_sum += w

    if weight_sum > 0:
        base_readiness = round(total_weighted / weight_sum, 1)
    else:
        base_readiness = 0.0

    # Boost slightly for completed mock interviews and quiz attempts
    completed_interviews = [m for m in mock_sessions if m.status == 'COMPLETED']
    passed_quizzes = [q for q in quiz_attempts if q.score_pct >= 70.0]
    
    training_bonus = min(5.0, len(completed_interviews) * 1.5 + len(passed_quizzes) * 0.5)
    overall_readiness_score = min(100.0, round(base_readiness + training_bonus, 1))

    # Readiness Tier
    if overall_readiness_score >= 85:
        readiness_tier = "Placement Ready (Tier 1 & Product Companies)"
    elif overall_readiness_score >= 70:
        readiness_tier = "Competent (Service & Core Tech Companies)"
    elif overall_readiness_score >= 50:
        readiness_tier = "Developing (Requires Focused Training)"
    elif overall_readiness_score > 0:
        readiness_tier = "Critical Remedial Required"
    else:
        readiness_tier = "Baseline Not Assessed"

    # Training Progress calculation:
    # Based on quizzes completed (target 5) + mock interviews (target 3) + videos completed
    completed_lessons = [l for l in (student.youtube_lessons or []) if l.is_completed]
    quiz_progress = min(1.0, len(quiz_attempts) / 5.0)
    interview_progress = min(1.0, len(completed_interviews) / 3.0)
    lesson_progress = min(1.0, len(completed_lessons) / 4.0)
    training_progress_pct = round(((quiz_progress * 0.4) + (interview_progress * 0.4) + (lesson_progress * 0.2)) * 100.0, 1)

    # Next Recommended Learning Activity
    next_activity = {
        'title': f"Master {weakest_domain['recommended_topic']}",
        'domain': weakest_domain['domain'],
        'type': 'YouTube Video Lesson & Quiz',
        'query': weakest_domain['recommended_query'],
        'description': f"Your {weakest_domain['domain']} score needs improvement. Watch the curated video lesson on {weakest_domain['recommended_topic']} and test your skills with a 5-question practice quiz."
    }

    return {
        'domains': evaluated_list,
        'domains_dict': domains_eval,
        'strongest_domain': strongest_domain,
        'weakest_domain': weakest_domain,
        'overall_readiness_score': overall_readiness_score,
        'readiness_tier': readiness_tier,
        'training_progress_pct': training_progress_pct,
        'next_activity': next_activity,
        'recent_quizzes': quiz_attempts[:5],
        'recent_interviews': mock_sessions[:5],
        'completed_interviews_count': len(completed_interviews),
        'quizzes_attempted_count': len(quiz_attempts),
        'lessons_completed_count': len(completed_lessons)
    }
