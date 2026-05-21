# Default role and permissions configuration
cs_default_role = "Student"
cs_default_permissions = {"view"}

# Define permissions for different roles
cs_permissions = {
    "Student": {
        "view",  # Can view course content
        "submit",  # Can submit assignments
    },
    "Instructor": {
        "view",  # Can view course content
        "view_all",  # Can view all student submissions
        "submit",  # Can submit assignments
        "submit_all",  # Can submit on behalf of others
        "grade",  # Can grade assignments
        "impersonate",  # Can view as another user
        "admin",  # Administrative access
        "groups",  # Can manage groups
        "checkoff"  # Can give checkoffs
    }
}

# User configuration settings
cs_user_config = {
    "section_variable": "section",  # Variable name for section
    "default_section_name": "default"  # Default section name
}

# Registration settings
cs_allow_registration = True  # Allow new user registration
cs_require_confirm_email = True  # Require email confirmation 