import base64
import io
import os
import sys
from datetime import datetime
from typing import Dict, List
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.interviewer import ExcelMockInterviewer, InterviewPhase

def process_question_text(question_text):
    if not question_text:
        return ""
    
    processed_text = question_text.replace('**', '')
    
    if '<div' in processed_text.lower() and 'table' in processed_text.lower():
        processed_text = processed_text.replace('<div class="table">', '<table class="table">')
        processed_text = processed_text.replace('</div>', '</table>' if '<table' in processed_text else '</div>')
    
    if '|' in processed_text and processed_text.count('|') > 2:
        lines = processed_text.split('\n')
        html_lines = []
        in_table = False
        
        for i, line in enumerate(lines):
            if '|' in line and line.strip().startswith('|') and line.strip().endswith('|'):
                if not in_table:
                    html_lines.append('<table border="1" style="border-collapse: collapse; margin: 10px 0;">')
                    in_table = True
                
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                
                if all(cell.replace('-', '').replace(' ', '') == '' for cell in cells):
                    continue
                
                is_header = not in_table
                tag = 'th' if is_header else 'td'
                
                row_html = '<tr>' + ''.join(f'<{tag} style="padding: 8px; border: 1px solid #ddd;">{cell}</{tag}>' for cell in cells) + '</tr>'
                html_lines.append(row_html)
            else:
                if in_table:
                    html_lines.append('</table>')
                    in_table = False
                html_lines.append(line)
        
        if in_table:
            html_lines.append('</table>')
        
        processed_text = '\n'.join(html_lines)
    
    processed_text = processed_text.replace('\n', '<br>')
    
    return processed_text

def main():
    st.set_page_config(
        page_title="AI-Powered Excel Mock Interviewer",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/your-repo',
            'Report a bug': 'https://github.com/your-repo/issues',
            'About': "AI-Powered Excel Mock Interviewer using Groq AI"
        }
    )
    
    st.markdown("""
    <style>
    .stApp {
        background-color: #f8f9fa;
        color: #212529;
    }
    
    .main-header {
        text-align: center;
        background: linear-gradient(90deg, #0056b3, #007bff);
        color: white;
        padding: 2rem;
        border-radius: 8px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .question-box {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border: 1px solid #dee2e6;
    }
    
    .feedback-box {
        background-color: #f8fff9;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border: 1px solid #dee2e6;
    }
    
    .user-answer-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
        border-left: 3px solid #6c757d;
        font-style: normal;
    }
    
    .score-card {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        text-align: center;
        border: 1px solid #dee2e6;
    }
    
    .stTextInput > div > div > input {
        background-color: #ffffff;
        color: #212529;
        border: 1px solid #ced4da;
    }
    
    .stTextArea > div > div > textarea {
        background-color: #ffffff;
        color: #212529;
        border: 1px solid #ced4da;
    }
    
    .stSelectbox > div > div > select {
        background-color: #ffffff;
        color: #212529;
        border: 1px solid #ced4da;
    }
    
    .stButton > button {
        background-color: #007bff !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 500 !important;
        font-size: 16px !important;
        transition: background-color 0.2s ease;
    }
    
    .stButton > button:hover {
        background-color: #0056b3 !important;
    }
    
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
        border-right: 1px solid #dee2e6;
    }
    
    .stProgress > div > div > div {
        background-color: #007bff;
    }
    
    .stTextArea .st-emotion-cache-1c7y2kd,
    .stTextArea .st-emotion-cache-16idsys p,
    .stTextArea [data-testid="stMarkdownContainer"] p,
    .stForm .st-emotion-cache-1c7y2kd,
    .stForm .st-emotion-cache-16idsys p,
    .stForm [data-testid="stMarkdownContainer"] p {
        display: none !important;
    }
    
    .stTextArea small,
    .stForm small,
    .st-emotion-cache-16idsys,
    [data-testid="stCaptionContainer"] {
        display: none !important;
    }
    
    .stForm [data-testid="stMarkdownContainer"]:last-child {
        display: none !important;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #007bff, #0056b3);
        color: white;
        padding: 1.5rem;
        border-radius: 8px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .phase-indicator {
        background-color: #e9ecef;
        padding: 0.75rem 1rem;
        border-radius: 6px;
        border-left: 4px solid #007bff;
        margin-bottom: 1rem;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)
    
    initialize_session_state()
    
    with st.sidebar:
        st.title("Interview Control")
        setup_api_key()
        show_progress()
        show_navigation_buttons()
    
    if st.session_state.get('show_setup', True):
        show_setup_page()
    elif st.session_state.get('interview_active', False):
        show_interview_page()
    elif st.session_state.get('show_results', False):
        show_results_page()
    else:
        show_welcome_page()

def initialize_session_state():
    if 'interviewer' not in st.session_state:
        st.session_state.interviewer = None
    if 'interview_active' not in st.session_state:
        st.session_state.interview_active = False
    if 'show_setup' not in st.session_state:
        st.session_state.show_setup = True
    if 'show_results' not in st.session_state:
        st.session_state.show_results = False
    if 'current_question' not in st.session_state:
        st.session_state.current_question = ""
    if 'feedback_history' not in st.session_state:
        st.session_state.feedback_history = []
    if 'api_key_validated' not in st.session_state:
        st.session_state.api_key_validated = False

def setup_api_key():
    st.subheader("API Configuration")
    
    env_api_key = os.getenv('GROQ_API_KEY')
    
    if env_api_key:
        api_option = st.radio(
            "Choose API Key Option:",
            ["Use Default (Free for Users)", "Use My Own API Key"],
            index=0,
            help="You can use the default API key or enter your own"
        )
        
        if api_option == "Use Default (Free for Users)":
            st.success("Using default API key - Ready to start!")
            st.session_state.api_key_validated = True
            st.session_state.groq_api_key = env_api_key
            return env_api_key
        else:
            api_key = st.text_input(
                "Enter your personal Groq API Key:",
                type="password",
                help="Get your free API key from https://console.groq.com",
                placeholder="gsk_..."
            )
            
            if api_key:
                with st.spinner("Validating API key..."):
                    is_valid = validate_api_key(api_key)
                
                if is_valid:
                    st.success("Personal API key validated!")
                    st.session_state.api_key_validated = True
                    st.session_state.groq_api_key = api_key
                    return api_key
                else:
                    st.error("Invalid API key. Please check and try again.")
                    st.error("Make sure your API key:")
                    st.write("   • Starts with 'gsk_'")
                    st.write("   • Is from https://console.groq.com")
                    st.write("   • Has sufficient credits/quota")
                    st.write("   • Is copied correctly (no extra spaces)")
            else:
                st.info("Enter your personal Groq API key or use the default option above")
    else:
        st.warning("No default API key available")
        api_key = st.text_input(
            "Enter your Groq API Key:",
            type="password",
            help="Get your free API key from https://console.groq.com"
        )
        
        if api_key:
            with st.spinner("Validating API key..."):
                is_valid = validate_api_key(api_key)
            
            if is_valid:
                st.success("API key validated!")
                st.session_state.api_key_validated = True
                st.session_state.groq_api_key = api_key
                return api_key
            else:
                st.error("Invalid API key. Please check and try again.")
                st.error("Make sure your API key:")
                st.write("   • Starts with 'gsk_'")
                st.write("   • Is from https://console.groq.com")
                st.write("   • Has sufficient credits/quota")
                st.write("   • Is copied correctly (no extra spaces)")
        
        st.info("Enter your Groq API key to start the interview")
    
    return None

def validate_api_key(api_key: str) -> bool:
    if not api_key or not api_key.strip():
        return False
    
    if not api_key.strip().startswith('gsk_'):
        return False
    
    try:
        from src.groq_ai_service import GroqAIService
        test_service = GroqAIService(api_key=api_key.strip())
        
        test_response = test_service.client.chat.completions.create(
            model="gemma2-9b-it",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5,
            temperature=0.1
        )
        
        return True
        
    except Exception as e:
        error_str = str(e).lower()
        if "unauthorized" in error_str or "invalid" in error_str or "authentication" in error_str:
            return False
        return False

def show_progress():
    if st.session_state.interviewer:
        state = st.session_state.interviewer.get_interview_state()
        
        st.subheader("Progress")
        
        progress = state['current_question_number'] / state['total_questions']
        st.progress(progress)
        
        st.write(f"Question: {state['current_question_number']}/{state['total_questions']}")
        st.write(f"Phase: {state['phase'].title()}")
        
        if hasattr(st.session_state.interviewer, 'evaluations') and st.session_state.interviewer.evaluations:
            avg_score = sum(e['overall_score'] for e in st.session_state.interviewer.evaluations) / len(st.session_state.interviewer.evaluations)
            st.metric("Current Average", f"{avg_score:.1f}/10")

def show_navigation_buttons():
    st.subheader("Controls")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Home", use_container_width=True):
            reset_to_welcome()
    
    with col2:
        if st.button("Restart", use_container_width=True):
            restart_interview()
    
    if st.session_state.interview_active:
        if st.button("Pause", use_container_width=True):
            st.session_state.interview_active = False
            st.rerun()

def show_welcome_page():
    st.markdown("""
    <div class="main-header">
        <h1>AI-Powered Excel Mock Interviewer</h1>
        <p>Assess your Excel proficiency with AI-generated questions and intelligent feedback</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### AI-Powered
        - Dynamic question generation
        - Intelligent answer evaluation
        - Personalized feedback
        """)
    
    with col2:
        st.markdown("""
        ### Comprehensive Assessment
        - Progressive difficulty levels
        - Multi-criteria evaluation
        - Detailed performance reports
        """)
    
    with col3:
        st.markdown("""
        ### Professional Ready
        - Real-world scenarios
        - Business-focused problems
        - Actionable recommendations
        """)
    
    st.markdown("---")
    st.subheader("How It Works")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **1. Setup**
        - Enter your Groq API key
        - Configure preferences
        - Start the assessment
        """)
    
    with col2:
        st.markdown("""
        **2. Interview**
        - Answer 3 AI-generated questions
        - Get immediate feedback
        - Progress through difficulty levels
        """)
    
    with col3:
        st.markdown("""
        **3. Results**
        - Comprehensive performance report
        - Detailed score breakdown
        - Personalized improvement plan
        """)
    
    st.markdown("---")
    
    if st.session_state.api_key_validated:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Start Excel Assessment", use_container_width=True, type="primary"):
                st.session_state.show_setup = False
                st.session_state.interview_active = True
                initialize_interviewer()
                st.rerun()
        
        if st.session_state.get('groq_api_key') == os.getenv('GROQ_API_KEY'):
            st.info("Using default API key - Free access for all users!")
        else:
            st.info("Using your personal API key")
    else:
        st.warning("Please configure your Groq API key in the sidebar to begin")

def show_setup_page():
    st.title("Interview Setup")
    
    if not st.session_state.api_key_validated:
        st.error("Please configure your Groq API key in the sidebar first")
        return
    
    st.success("API key configured. Ready to start!")
    
    st.subheader("Interview Preferences")
    
    col1, col2 = st.columns(2)
    
    with col1:
        difficulty_start = st.selectbox(
            "Starting Difficulty Level:",
            ["Intermediate", "Intermediate-Advanced", "Advanced"],
            index=0,
            help="Choose your preferred starting difficulty"
        )
    
    with col2:
        question_count = st.slider(
            "Number of Questions:",
            min_value=3,
            max_value=5,
            value=3,
            help="Total number of questions in the assessment"
        )
    
    st.subheader("Preparation Tips")
    st.markdown("""
    **For best results:**
    - Be specific about Excel functions and formulas
    - Explain your reasoning step-by-step
    - Mention alternative approaches when possible
    - Use proper Excel terminology
    - Don't worry if you're unsure - give your best answer!
    """)
    
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Begin Interview", use_container_width=True, type="primary"):
            st.session_state.show_setup = False
            st.session_state.interview_active = True
            st.session_state.selected_question_count = question_count
            st.session_state.selected_difficulty = difficulty_start
            initialize_interviewer()
            st.rerun()

def show_interview_page():
    if not st.session_state.interviewer:
        st.error("Interview not properly initialized. Please restart.")
        return
    
    interviewer = st.session_state.interviewer
    state = interviewer.get_interview_state()
    
    st.title("Excel Proficiency Interview")
    
    current_phase = state['phase']
    st.markdown(f'<div class="phase-indicator">Phase: {current_phase.title()}</div>', unsafe_allow_html=True)
    
    if current_phase == 'introduction':
        handle_introduction_phase(interviewer)
    elif current_phase == 'questioning':
        handle_questioning_phase(interviewer, state)
    elif current_phase == 'conclusion':
        handle_conclusion_phase(interviewer)

def handle_introduction_phase(interviewer):
    intro_text = interviewer.start_interview()
    st.markdown(f"""
    <div class="question-box">
        <div style="font-size: 16px; line-height: 1.6;">
            {intro_text.replace('Hello!', 'Hello!')}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("I'm Ready to Begin!", use_container_width=True, type="primary"):
            response = interviewer.process_user_input("ready")
            st.session_state.current_question = response
            st.rerun()

def handle_questioning_phase(interviewer, state):
    if st.session_state.feedback_history:
        st.subheader("Interview Progress")
        
        for i, feedback in enumerate(st.session_state.feedback_history):
            st.markdown(f"""
            <div class="question-box">
                <h4>Question {feedback['question_number']} of {state['total_questions']}</h4>
                {process_question_text(feedback['question'])}
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="feedback-box">
                <strong>Your Answer:</strong><br>
                <div class="user-answer-box">
                {feedback['answer']}
                </div>
                <strong>AI Feedback:</strong><br>
                {feedback['feedback']}
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
    
    if st.session_state.current_question and state['current_question_number'] <= state['total_questions']:
        st.markdown(f"""
        <div class="question-box">
            <h4>Question {state['current_question_number']} of {state['total_questions']}</h4>
            {process_question_text(st.session_state.current_question)}
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("Your Answer")
        user_answer = st.text_area(
            "Provide your detailed answer:",
            height=150,
            placeholder="Explain your Excel approach step-by-step. Include specific functions, formulas, and reasoning...",
            help="Be specific about Excel functions and explain your reasoning clearly.",
            key=f"answer_{state['current_question_number']}"
        )
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Submit Answer", use_container_width=True, type="primary", disabled=not user_answer.strip()):
                if user_answer.strip():
                    with st.spinner("AI is evaluating your answer..."):
                        response = interviewer.process_user_input(user_answer)
                    
                    current_state = interviewer.get_interview_state()
                    
                    if current_state['phase'] == 'conclusion':
                        interviewer.phase = InterviewPhase.CONCLUSION
                        with st.spinner("Generating your comprehensive performance report..."):
                            final_report = interviewer._handle_conclusion_phase()
                        st.session_state.final_report = final_report
                        st.session_state.show_results = True
                        st.session_state.interview_active = False
                    else:
                        feedback_only = response
                        next_question = None
                        
                        if "**Question" in response:
                            parts = response.split("**Question", 1)
                            feedback_only = parts[0].strip()
                            if len(parts) > 1:
                                next_question = "**Question" + parts[1]
                        
                        st.session_state.feedback_history.append({
                            'question_number': state['current_question_number'],
                            'question': st.session_state.current_question,
                            'answer': user_answer,
                            'feedback': feedback_only,
                            'timestamp': datetime.now()
                        })
                        
                        if next_question:
                            st.session_state.current_question = next_question
                    
                    st.rerun()

def handle_conclusion_phase(interviewer):
    st.success("Interview Complete!")
    
    with st.spinner("Generating your comprehensive performance report..."):
        final_report = interviewer._handle_conclusion_phase()
    
    st.session_state.final_report = final_report
    st.session_state.show_results = True
    st.session_state.interview_active = False
    st.rerun()

def show_results_page():
    st.title("Your Excel Proficiency Report")
    
    if 'final_report' not in st.session_state:
        if (st.session_state.interviewer and 
            st.session_state.feedback_history and 
            len(st.session_state.feedback_history) >= 3):
            
            st.info("Generating missing report...")
            try:
                with st.spinner("Generating your comprehensive performance report..."):
                    final_report = st.session_state.interviewer._handle_conclusion_phase()
                st.session_state.final_report = final_report
                st.rerun()
            except Exception as e:
                st.error(f"Error generating report: {str(e)}")
                return
        else:
            st.error("No report available. Please complete the interview first.")
            return
    
    st.markdown(st.session_state.final_report)
    
    if st.session_state.interviewer and st.session_state.interviewer.evaluations:
        show_performance_charts()
    
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Take Another Assessment", use_container_width=True):
            restart_interview()
    
    with col2:
        if st.button("Download PDF Report", use_container_width=True):
            download_report()
    
    with col3:
        if st.button("Back to Home", use_container_width=True):
            reset_to_welcome()

def show_performance_charts():
    evaluations = st.session_state.interviewer.evaluations
    
    if not evaluations:
        return
    
    st.subheader("Performance Visualization")
    
    categories = ['Correctness', 'Efficiency', 'Clarity']
    scores = [
        sum(e['correctness_score'] for e in evaluations) / len(evaluations),
        sum(e['efficiency_score'] for e in evaluations) / len(evaluations),
        sum(e['clarity_score'] for e in evaluations) / len(evaluations)
    ]
    
    fig = go.Figure(data=go.Scatterpolar(
        r=scores,
        theta=categories,
        fill='toself',
        name='Your Scores'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10]
            )),
        showlegend=True,
        title="Performance Breakdown"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        for i, (category, score) in enumerate(zip(categories, scores)):
            color = "#28a745" if score >= 7 else "#ffc107" if score >= 5 else "#dc3545"
            st.markdown(f"""
            <div class="score-card" style="border-left: 4px solid {color};">
                <h4>{category}</h4>
                <h2>{score:.1f}/10</h2>
            </div>
            """, unsafe_allow_html=True)

def download_report():
    if 'final_report' in st.session_state:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, letter
            from reportlab.lib.styles import (ParagraphStyle,
                                              getSampleStyleSheet)
            from reportlab.lib.units import inch
            from reportlab.platypus import (PageBreak, Paragraph,
                                            SimpleDocTemplate, Spacer)

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, 
                                  topMargin=72, bottomMargin=18)
            
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                textColor=colors.darkblue,
                alignment=1
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                textColor=colors.darkblue
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=11,
                spaceAfter=6,
                leftIndent=12
            )
            
            story = []
            
            story.append(Paragraph("Excel Proficiency Assessment Report", title_style))
            story.append(Spacer(1, 12))
            
            timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
            story.append(Paragraph(f"<b>Generated:</b> {timestamp}", normal_style))
            story.append(Spacer(1, 20))
            
            report_content = st.session_state.final_report
            
            lines = report_content.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 6))
                    continue
                
                if line.startswith('##') or line.startswith('# '):
                    heading_text = line.replace('##', '').replace('#', '').strip()
                    story.append(Paragraph(heading_text, heading_style))
                elif line.startswith('**') and line.endswith('**'):
                    bold_text = line.replace('**', '')
                    story.append(Paragraph(f"<b>{bold_text}</b>", normal_style))
                elif line.startswith('- ') or line.startswith('• '):
                    bullet_text = line[2:].strip()
                    story.append(Paragraph(f"• {bullet_text}", normal_style))
                else:
                    clean_line = line.replace('**', '').replace('*', '').replace('`', '')
                    if clean_line:
                        story.append(Paragraph(clean_line, normal_style))
            
            doc.build(story)
            
            pdf_data = buffer.getvalue()
            buffer.close()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Excel_Assessment_Report_{timestamp}.pdf"
            
            st.download_button(
                label="Download PDF Report",
                data=pdf_data,
                file_name=filename,
                mime="application/pdf"
            )
            
        except ImportError:
            report_content = st.session_state.final_report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Excel_Assessment_Report_{timestamp}.txt"
            
            st.download_button(
                label="Download Text Report (Fallback)",
                data=report_content,
                file_name=filename,
                mime="text/plain"
            )
        except Exception as e:
            st.error(f"Error generating PDF: {str(e)}")
            report_content = st.session_state.final_report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Excel_Assessment_Report_{timestamp}.txt"
            
            st.download_button(
                label="Download Text Report (Fallback)",
                data=report_content,
                file_name=filename,
                mime="text/plain"
            )

def initialize_interviewer():
    api_key = st.session_state.get('groq_api_key') or os.getenv('GROQ_API_KEY')
    question_count = st.session_state.get('selected_question_count', 3)
    st.session_state.interviewer = ExcelMockInterviewer(groq_api_key=api_key, total_questions=question_count)

def restart_interview():
    st.session_state.interview_active = False
    st.session_state.show_results = False
    st.session_state.show_setup = True
    st.session_state.current_question = ""
    st.session_state.feedback_history = []
    if 'final_report' in st.session_state:
        del st.session_state.final_report
    if 'interviewer' in st.session_state:
        del st.session_state.interviewer
    st.rerun()

def reset_to_welcome():
    st.session_state.interview_active = False
    st.session_state.show_results = False
    st.session_state.show_setup = True
    st.session_state.current_question = ""
    st.session_state.feedback_history = []
    if 'final_report' in st.session_state:
        del st.session_state.final_report
    st.rerun()

if __name__ == "__main__":
    main()
