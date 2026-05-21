import urllib.request
import json

def handle(context):
    path = context['cs_path_info']
    method = context['cs_method']
    body = context['cs_request_content']
    query = context['cs_query_string'].decode() if context['cs_query_string'] else ""

    base = "http://127.0.0.1:8001"
    url = base + "/" + "/".join(path)
    if query:
        url += "?" + query

    req = urllib.request.Request(url, data=body, method=method)
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return (str(resp.status), 'OK'), {'Content-Type': 'application/json'}, resp.read()
    except Exception as e:
        return ('500', 'Internal Error'), {}, f"Proxy error: {str(e)}".encode()