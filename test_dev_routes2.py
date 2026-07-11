import subprocess
import time
import sys
import urllib.request
import urllib.error

with open(r"C:\Users\Poulabi Ghosh\Downloads\Agentic AI\test_output2.txt", "w", encoding="utf-8") as out:
    out.write("[TEST] Starting dev server for route debugging...\n")
    
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
                body = resp.read().decode('utf-8', errors='replace')
                return resp.status, headers, body
        except urllib.error.HTTPError as e:
            headers = dict(e.headers)
            body = e.read().decode('utf-8', errors='replace')
            return e.code, headers, body
        except Exception as e:
            return None, {}, str(e)
    
    # Get the full HTML for the 404 page
    out.write("\n[TEST] Getting full 404 page HTML...\n")
    status, headers, body = req_full("http://127.0.0.1:3000/projects/test-id/agent-workspace")
    out.write(f"Status: {status}\n")
    out.write(f"Content-Type: {headers.get('Content-Type', 'N/A')}\n")
    out.write(f"Body length: {len(body)}\n")
    out.write(f"Body:\n{body}\n")
    
    # Also check if the route /projects/test-id/papers works with full HTML
    out.write("\n[TEST] Getting full 404 for /projects/test-id/papers...\n")
    status, headers, body = req_full("http://127.0.0.1:3000/projects/test-id/papers")
    out.write(f"Status: {status}\n")
    out.write(f"Body length: {len(body)}\n")
    
    out.write("\n[TEST] Cleaning up...\n")
    frontend.terminate()
    frontend.wait(timeout=5)
    out.write("[TEST] Done\n")
