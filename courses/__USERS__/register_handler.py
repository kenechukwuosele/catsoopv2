import os
import json
import hashlib
import secrets
import stat
import tempfile
import re

ROLE_PERMISSIONS = {
    "Student": {
        "view", "submit", "view_grades", "view_handouts", 
        "take_quiz", "view_announcements"
    },
    "Instructor": {
        "view_all", "submit_all", "grade", "manage", "create_quiz", 
        "edit_quiz", "view_all_grades", "create_announcements", 
        "manage_students", "view_analytics", "edit_content"
    }
}

def hash_password(password):
    """Secure PBKDF2 password hashing"""
    if not password:
        raise ValueError("Password required")
    salt = secrets.token_hex(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), 
                                salt.encode('utf-8'), 100000)
    return f"{salt}:{pwdhash.hex()}"

def validate_registration_data(form_data):
    """Validate all registration inputs"""
    errors = []
    uname = form_data.get("uname", "").strip()
    email = form_data.get("email", "").strip()
    name = form_data.get("name", "").strip() or uname
    role = form_data.get("role", "Student")
    password = form_data.get("passwd", "")
    
    if not (3 <= len(uname) <= 20):
        errors.append("Username: 3-20 characters")
    if not re.match(r"^[a-zA-Z0-9_-]+$", uname):
        errors.append("Username: letters, numbers, _, - only")
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        errors.append("Valid email required")
    if len(password) < 6:
        errors.append("Password: 6+ characters")
    if role not in ROLE_PERMISSIONS:
        errors.append(f"Invalid role: {role}")
    
    if errors:
        raise ValueError("; ".join(errors))
    return uname, email, name, role, password

def handle_registration(context, form_data):
    """
    Handle registration with full validation and security.
    """
    try:
        context["csm_cslog"].update_log("_registration_debug", [], "debug", "Starting registration")
        
        # 1. VALIDATE INPUT
        uname, email, name, role, password = validate_registration_data(form_data)
        context["csm_cslog"].update_log("_registration_debug", [], "validated", 
            f"User: {uname}, Role: {role}")
        
        # 2. CHECK DUPLICATES
        user_dir = os.path.join(context["cs_data_root"], "courses", "__USERS__")
        user_file = os.path.abspath(os.path.join(user_dir, f"{uname}.py"))
        
        if os.path.exists(user_file):
            raise ValueError(f"Username '{uname}' already exists")
        if context["csm_cslog"].read_log("_logininfo", [], uname):
            raise ValueError(f"Username '{uname}' already registered")
        
        # 3. CREATE USER DIRECTORY
        os.makedirs(user_dir, exist_ok=True)
        
        # 4. CREATE USER FILE (your existing logic - perfect!)
        permissions = ROLE_PERMISSIONS[role]
        file_content = f"""role = {repr(role)}
permissions = {repr(permissions)}
email = {repr(email)}
name = {repr(name)}
"""
        
        temp_file = os.path.join(user_dir, f".{uname}.tmp")
        with open(temp_file, "w") as f:
            f.write(file_content)
        os.chmod(temp_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        os.rename(temp_file, user_file)
        
        # 5. STORE SECURE LOGIN INFO
        password_hash = hash_password(password)
        login_info = {
            "email": email,
            "name": name,
            "confirmed": True,
            "role": role,
            "password_hash": password_hash,  # ✅ SECURE
            "permissions": list(permissions)
        }
        
        context["csm_cslog"].update_log("_logininfo", [], uname, login_info)
        
        context["csm_cslog"].update_log("_registration_debug", [], "success", 
            f"✅ Registered {uname} ({role})")
        return True
        
    except Exception as e:
        context["csm_cslog"].update_log("_registration_debug", [], "error", str(e))
        # Cleanup temp file
        if 'temp_file' in locals() and os.path.exists(temp_file):
            try: os.remove(temp_file)
            except: pass
        raise