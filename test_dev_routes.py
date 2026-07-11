import subprocess
import time
import sys
import urllib.request
import urllib.error

# Redirect stdout to file to avoid encoding issues
with open(r"C:\Users\Poulabi Ghosh\Downloads\Agentic AI\test_output.txt", "w", encoding="utf-8") as out:
    out.write("[TEST] Starting dev server for route debugging...\n")
    
    # Start frontend
    frontend_cmd = r'cd /d "C:\Users\Poulabi Ghosh\Downloads\Agentic AI\aara-frontend" && node_modules\.bin\next.cmd dev --port 3000'
    out.write("[TEST] Starting frontend on port 3000...\n")
    frontend = subprocess.Popen(
        frontend_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    
    out.write("[TEST] Waiting for dev server to start...\n")
    time.sleep(20)
    
    if frontend.poll() is not None:
        out.write("[TEST] Frontend failed to start\n")
        stdout, stderr = frontend.communicate()
        try:
            err_text = stderr.decode('utf-8', errors='replace')[-1500:]
        except:
            err_text = str(stderr)[-1500:]
        out.write("STDERR: " + err_text + "\n")
        sys.exit(1)
    
    out.write("[TEST] Dev server is running\n")
    
    def req_full(url, method="GET"):
        try:
            rq = urllib.request.Request(url, method=method)
            with urllib.request.urlopen(rq, timeout=10) as resp:
                headers = dict(resp.headers)
                body = resp.read().decode('utf-8', errors='replace')[:500]
                return resp.status, headers, body
        except urllib.error.HTTPError as e:
            headers = dict(e.headers)
            body = e.read().decode('utf-8', errors='replace')[:500]
            return e.code, headers, body
        except Exception as e:
            return None, {}, str(e)
    
    # Test various routes with full response details
    out.write("\n[TEST] Testing routes with full response details...\n")
    routes = [
        ("GET", "http://127.0.0.1:3000/projects/test-id"),
        ("GET", "http://127.0.0.1:3000/projects/test-id/"),
        ("GET", "http://127.0.0.1:3000/projects/test-id/agent-workspace"),
        ("GET", "http://127.0.0.1:3000/projects/test-id/agent-workspace/"),
        ("GET", "http://127.0.0.1:3000/projects/test-id/timeline"),
        ("GET", "http://127.0.0.1:3000/projects/test-id/papers"),
    ]
    
    for method, url in routes:
        status, headers, body = req_full(url, method)
        out.write(f"\n  {method} {url}\n")
        out.write(f"    Status: {status}\n")
        out.write(f"    Content-Type: {headers.get('Content-Type', 'N/A')}\n")
        out.write(f"    Body preview: {body[:300].replace(chr(10), ' ')}\n")
    
    out.write("\n[TEST] Cleaning up...\n")
    frontend.terminate()
    frontend.wait(timeout=5)
    out.write("[TEST] Done\n")
