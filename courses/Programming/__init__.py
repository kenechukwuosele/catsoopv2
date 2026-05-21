# -*- mode: python -*-
# python 3
import json
import os

def _deny_unenrolled(context):
    context["cs_content_header"] = "Enrollment required"
    context["cs_content"] = (
        "<div style=\"padding:20px;\">"
        "<p>You are not enrolled in this course.</p>"
        "<p><a href=\"/\">Go to Home to enroll.</a></p>"
        "</div>"
    )
    context["cs_handler"] = "passthrough"


def cs_pre_handle(context):
    user_info = context.get("cs_user_info", {}) or {}
    if user_info.get("role") == "Instructor":
        return
    username = user_info.get("username") or context.get("cs_username")
    if not username:
        _deny_unenrolled(context)
        return
    log = context.get("csm_cslog")
    if not log:
        return
    enrolled = log.read_log("_course_enrollments", [], username) or []
    if isinstance(enrolled, dict):
        enrolled = enrolled.get("courses", [])
    if isinstance(enrolled, str):
        enrolled = [v.strip() for v in enrolled.split(",") if v.strip()]
    if context.get("cs_course") not in enrolled:
        _deny_unenrolled(context)

# --- Course Configuration ---
cs_course_name = "Programming"
cs_course_title = "Introduction to Programming"

cs_template = {
    'header': '''
    <div class="course-header">
        <h1>{course_title}</h1>
        <nav class="course-nav">
            <ul>
                <li><a href="{base_url}/content">Home</a></li>
                <li><a href="{base_url}/week1">Week 1</a></li>
                <li><a href="{base_url}/week4">Week 4: Functions</a></li>
            </ul>
        </nav>
    </div>
    ''',
    'footer': '''
    <div class="course-footer">
        <p>&copy; 2025 Programming Course</p>
    </div>
    '''
}

problem_title = "Integrated Quiz System"

def render(context):
    # 1. DATA PATH SETUP
    # We store data in the user's private directory so it persists across sessions
    user_dir = context.get('cs_user_dir')
    data_file = os.path.join(user_dir, "saved_questions.json") if user_dir else None

    # 2. HANDLE AJAX POST REQUESTS
    request_data = context.get('cs_request_data', {})
    action = request_data.get('cs_action')

    if action:
        # CSRF Security Check
        submitted_token = request_data.get('csrf_token')
        session_token = context.get('cs_session_data', {}).get('csrf_token', '')
        
        if not submitted_token or submitted_token != session_token:
            return json.dumps({'success': False, 'error': 'Security Validation Failed'})

        if action == 'save_question':
            try:
                # Parse incoming data
                new_question = {
                    'text': request_data.get('question_text'),
                    'type': request_data.get('question_type'),
                    'options': json.loads(request_data.get('options', '[]')),
                    'correct_answers': json.loads(request_data.get('correct_answers', '[]'))
                }

                # Load existing data
                questions = []
                if data_file and os.path.exists(data_file):
                    with open(data_file, 'r') as f:
                        questions = json.load(f)

                # Add and save
                questions.append(new_question)
                if data_file:
                    with open(data_file, 'w') as f:
                        json.dump(questions, f)

                return json.dumps({'success': True, 'message': 'Question saved successfully!'})
            
            except Exception as e:
                return json.dumps({'success': False, 'error': str(e)})

    # 3. RENDER UI (GET REQUEST)
    csrf_token = context.get('cs_session_data', {}).get('csrf_token', '')
    username = context.get('cs_user_info', {}).get('username', 'Guest')

    # Load existing questions to display on page load
    existing_questions_json = "[]"
    if data_file and os.path.exists(data_file):
        try:
            with open(data_file, 'r') as f:
                existing_questions_json = f.read()
        except:
            pass

    cs_content = f"""
    <style>
        .quiz-container {{ font-family: sans-serif; max-width: 800px; margin: 20px auto; padding: 20px; border: 1px solid #ccc; border-radius: 8px; }}
        .tab-content {{ padding: 20px; border: 1px solid #ddd; border-top: none; }}
        .form-group {{ margin-bottom: 15px; }}
        label {{ display: block; font-weight: bold; margin-bottom: 5px; }}
        input[type="text"], select {{ width: 100%; padding: 8px; box-sizing: border-box; }}
        .btn {{ background: #007bff; color: white; border: none; padding: 10px 15px; cursor: pointer; border-radius: 4px; }}
        .btn:hover {{ background: #0056b3; }}
        #status-msg {{ margin-top: 10px; color: green; font-weight: bold; }}
    </style>

    <div class="quiz-container" 
         id="quiz-app" 
         data-csrf="{csrf_token}" 
         data-username="{username}">
        
        <h2>{problem_title}</h2>
        <p>Logged in as: <strong>{username}</strong></p>

        <div class="tab-content">
            <form id="question-form">
                <div class="form-group">
                    <label>Question Text</label>
                    <input type="text" id="q-text" placeholder="Enter question here..." required>
                </div>
                <div class="form-group">
                    <label>Type</label>
                    <select id="q-type">
                        <option value="multiple_choice">Multiple Choice</option>
                        <option value="short_answer">Short Answer</option>
                    </select>
                </div>
                <button type="submit" class="btn">Save Question</button>
            </form>
            <div id="status-msg"></div>
        </div>

        <hr>
        <h3>Your Saved Questions</h3>
        <div id="questions-list"></div>
    </div>

    <script>
    (function() {{
        const app = document.getElementById('quiz-app');
        const config = app.dataset;
        const form = document.getElementById('question-form');
        const status = document.getElementById('status-msg');
        const listDisplay = document.getElementById('questions-list');

        // Initial load of questions from the server-injected JSON
        let savedQuestions = {existing_questions_json};

        function renderList() {{
            if (savedQuestions.length === 0) {{
                listDisplay.innerHTML = "<em>No questions saved yet.</em>";
                return;
            }}
            listDisplay.innerHTML = "<ul>" + savedQuestions.map(q => `<li><strong>${{q.text}}</strong> (${{q.type}})</li>`).join('') + "</ul>";
        }}

        async function handleSave(e) {{
            e.preventDefault();
            status.textContent = "Saving...";

            const payload = {{
                question_text: document.getElementById('q-text').value,
                question_type: document.getElementById('q-type').value,
                options: [], // Add logic to collect these if needed
                correct_answers: []
            }};

            const formData = new FormData();
            formData.append('cs_action', 'save_question');
            formData.append('csrf_token', config.csrf);
            formData.append('question_text', payload.question_text);
            formData.append('question_type', payload.question_type);
            formData.append('options', JSON.stringify(payload.options));
            formData.append('correct_answers', JSON.stringify(payload.correct_answers));

            try {{
                const response = await fetch("", {{
                    method: 'POST',
                    body: formData
                }});
                const result = await response.json();

                if (result.success) {{
                    status.style.color = "green";
                    status.textContent = result.message;
                    // Update local UI
                    savedQuestions.push(payload);
                    renderList();
                    form.reset();
                }} else {{
                    throw new Error(result.error);
                }}
            }} catch (err) {{
                status.style.color = "red";
                status.textContent = "Error: " + err.message;
            }}
        }}

        form.addEventListener('submit', handleSave);
        renderList();
    }})();
    </script>
    """
    return cs_content
