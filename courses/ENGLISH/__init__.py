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
