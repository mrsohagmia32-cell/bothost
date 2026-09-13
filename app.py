import os
import subprocess
import threading
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

bot_process = None
bot_logs = []
LOG_LIMIT = 200


def read_output(process):
  global bot_logs
  for line in iter(process.stdout.readline, b""):
    decoded_line = line.decode("utf-8", errors="ignore")
    bot_logs.append(decoded_line)
    if len(bot_logs) > LOG_LIMIT:
      bot_logs.pop(0)
  process.stdout.close()


@app.route("/")
def index():
  return render_template_string(HTML_TEMPLATE)


@app.route("/start", methods=["POST"])
def start_bot():
  global bot_process, bot_logs
  if bot_process and bot_process.poll() is None:
    return jsonify(
        {"status": "error", "message": "Bot is already running!"}
    )

  data = request.json
  code = data.get("code", "")

  if not code.strip():
    return jsonify({"status": "error", "message": "Python code cannot be empty!"})

  bot_filename = "temp_bot.py"
  with open(bot_filename, "w", encoding="utf-8") as f:
    f.write(code)

  bot_logs = ["[INFO] Starting Telegram Bot...\n"]

  try:
    bot_process = subprocess.Popen(
        ["python", bot_filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )

    t = threading.Thread(target=read_output, args=(bot_process,))
    t.daemon = True
    t.start()

    return jsonify({"status": "success", "message": "Bot started successfully!"})
  except Exception as e:
    return jsonify({"status": "error", "message": str(e)})


@app.route("/stop", methods=["POST"])
def stop_bot():
  global bot_process, bot_logs
  if bot_process and bot_process.poll() is None:
    bot_process.terminate()
    bot_process = None
    bot_logs.append("\n[INFO] Bot stopped by user.\n")
    return jsonify({"status": "success", "message": "Bot stopped successfully!"})
  return jsonify({"status": "error", "message": "No running bot found."})


@app.route("/logs", methods=["GET"])
def get_logs():
  global bot_process, bot_logs
  is_running = bot_process is not None and bot_process.poll() is None
  return jsonify({"running": is_running, "logs": "".join(bot_logs)})


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Bot Web Panel</title>
    <style>
        body { font-family: Arial, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
        .container { max-width: 900px; margin: auto; background: #1e293b; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        h2 { text-align: center; color: #38bdf8; }
        label { display: block; margin-top: 15px; font-weight: bold; color: #cbd5e1; }
        textarea { width: 100%; height: 280px; background: #0f172a; color: #38bdf8; border: 1px solid #475569; border-radius: 6px; padding: 12px; font-family: monospace; font-size: 14px; resize: vertical; box-sizing: border-box; }
        .btn-group { margin-top: 15px; display: flex; gap: 10px; }
        button { flex: 1; padding: 12px; border: none; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        #startBtn { background: #22c55e; color: white; }
        #startBtn:hover { background: #16a34a; }
        #stopBtn { background: #ef4444; color: white; }
        #stopBtn:hover { background: #dc2626; }
        .status-box { margin-top: 20px; padding: 12px; background: #0f172a; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #475569; }
        pre { background: #090d16; color: #4ade80; padding: 15px; border-radius: 6px; height: 250px; overflow-y: auto; font-family: monospace; font-size: 13px; border: 1px solid #334155; margin-top: 10px; box-sizing: border-box; }
        .indicator { width: 12px; height: 12px; border-radius: 50%; display: inline-block; background: #ef4444; margin-right: 6px; }
        .indicator.active { background: #22c55e; box-shadow: 0 0 8px #22c55e; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Telegram Bot Web Panel</h2>
        
        <label>Paste Python Bot Code:</label>
        <textarea id="botCode" placeholder="# Paste your python telegram bot code here..."></textarea>
        
        <div class="btn-group">
            <button id="startBtn" onclick="startBot()">Start Bot</button>
            <button id="stopBtn" onclick="stopBot()">Stop Bot</button>
        </div>

        <div class="status-box">
            <div>Status: <span id="statusIndicator" class="indicator"></span><span id="statusText">Stopped</span></div>
            <input type="file" id="fileInput" accept=".py" style="display:none" onchange="loadFile(event)">
            <button style="background:#334155; color:white; padding:8px 12px; flex:unset; font-size:13px;" onclick="document.getElementById('fileInput').click()">Upload .py File</button>
        </div>

        <label>Live Console Logs:</label>
        <pre id="consoleLogs">Waiting for logs...</pre>
    </div>

    <script>
        function loadFile(event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('botCode').value = e.target.result;
                };
                reader.readAsText(file);
            }
        }

        function startBot() {
            const code = document.getElementById('botCode').value;
            fetch('/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code: code })
            })
            .then(res => res.json())
            .then(data => {
                alert(data.message);
                fetchLogs();
            });
        }

        function stopBot() {
            fetch('/stop', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                alert(data.message);
                fetchLogs();
            });
        }

        function fetchLogs() {
            fetch('/logs')
            .then(res => res.json())
            .then(data => {
                const logBox = document.getElementById('consoleLogs');
                logBox.textContent = data.logs || "No logs available.";
                logBox.scrollTop = logBox.scrollHeight;

                const indicator = document.getElementById('statusIndicator');
                const statusText = document.getElementById('statusText');
                if (data.running) {
                    indicator.classList.add('active');
                    statusText.textContent = "Running";
                } else {
                    indicator.classList.remove('active');
                    statusText.textContent = "Stopped";
                }
            });
        }

        setInterval(fetchLogs, 2000);
    </script>
</body>
</html>
"""

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
