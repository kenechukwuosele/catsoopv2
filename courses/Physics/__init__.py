# Course configuration
import json

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

cs_course_name = "Programming"
cs_course_title = "Introduction to Programming"

# Course template settings
cs_template = {
    'header': '''
    <div class="course-header">
        <h1>{course_title}</h1>
        <nav class="course-nav">
            <ul>
                <li><a href="{base_url}/content">Home</a></li>
                <li><a href="{base_url}/week1">Week 1: Introduction</a></li>
                <li><a href="{base_url}/week2">Week 2: Basic Concepts</a></li>
                <li><a href="{base_url}/week3">Week 3: Control Structures</a></li>
                <li><a href="{base_url}/week4">Week 4: Functions</a></li>
                <li><a href="{base_url}/week5">Week 5: Data Structures</a></li>
            </ul>
        </nav>
    </div>
    ''',
    'footer': '''
    <div class="course-footer">
        <p>&copy; 2024 Programming Course</p>
    </div>
    '''
}

# Course-wide settings
cs_course_contact = "instructor@example.com"
cs_course_website = "https://example.com/course" 


# -*- mode: python -*-
# python 3

problem_title = "Integrated Quiz System"

def render(context):
    cs_content = """
    <style>
    /* Your existing CSS styles */
    </style>

    <div class="tab">
        <!-- Your existing HTML tabs -->
    </div>

    <div id="catsoop-auth-data" 
         data-csrf="%s" 
         data-username="%s"
         style="display:none;"></div>

    <script>
    // Authentication data
    const AUTH = {
        csrf: "%s",
        username: "%s"
    };

    async function makeAjaxRequest(action, data = {}) {
        const formData = new FormData();
        formData.append('cs_action', action);
        formData.append('csrf_token', AUTH.csrf);
        formData.append('username', AUTH.username);
        
        // Add other data
        for (const [key, value] of Object.entries(data)) {
            if (value !== undefined) formData.append(key, value);
        }

        try {
            const response = await fetch("", {
                method: 'POST',
                body: formData,
                credentials: 'same-origin'
            });
            
            const result = await response.text();
            return JSON.parse(result);
            
        } catch (error) {
            console.error("AJAX Error:", error);
            throw error;
        }
    }

    // Your existing addQuestion function
    async function addQuestion(e) {
        e.preventDefault();
        try {
            // ... collect question data ...
            
            const result = await makeAjaxRequest('save_question', {
                question_text: questionText,
                question_type: questionType,
                options: JSON.stringify(options),
                correct_answers: JSON.stringify(correctAnswers)
            });

            if (result.success) {
                // Handle success
            } else {
                alert(result.error || "Failed to save question");
            }
        } catch (error) {
            alert("Error: " + error.message);
        }
    }

    // Other existing JavaScript functions...
    </script>
    """ % (context['cs_session_data'].get('csrf_token', ''),
           context['cs_user_info'].get('username', ''),
           context['cs_session_data'].get('csrf_token', ''),
           context['cs_user_info'].get('username', ''))

    # Check for POST requests (backend processing)
    if context['cs_request_data'].get('cs_action', '') == 'save_question':
        # Verify CSRF
        submitted_token = context['cs_request_data'].get('csrf_token', '')
        if submitted_token != context['cs_session_data'].get('csrf_token', ''):
            return {'error': 'Invalid CSRF token'}
        
        # Process question data
        try:
            question_data = {
                'text': context['cs_request_data']['question_text'],
                'type': context['cs_request_data']['question_type'],
                'options': json.loads(context['cs_request_data']['options']),
                'correct_answers': json.loads(context['cs_request_data']['correct_answers'])
            }
            
            # [Your save logic here - example:]
            # if 'questions' not in context['cs_session_data']:
            #     context['cs_session_data']['questions'] = []
            # context['cs_session_data']['questions'].append(question_data)
            
            return {'success': True, 'message': 'Question saved'}
        except Exception as e:
            return {'error': f"Error saving question: {str(e)}"}

    return cs_content
