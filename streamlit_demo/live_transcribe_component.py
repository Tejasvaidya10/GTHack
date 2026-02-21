"""Live transcription Streamlit component.

Renders an HTML/JS component that captures mic audio via MediaRecorder,
sends chunks over WebSocket to the FastAPI backend, and displays
the live transcript as results come back.
"""

import requests
import streamlit as st
import streamlit.components.v1 as components
from datetime import date

API_BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"


def _get_live_transcribe_html(session_id: str, ws_url: str) -> str:
    """Generate the HTML/JS for the live recording component."""
    return f"""
<!DOCTYPE html>
<html>
<head>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 16px; background: transparent; }}

  .controls {{
    display: flex; align-items: center; gap: 12px; margin-bottom: 16px;
  }}
  button {{
    padding: 10px 24px; border: none; border-radius: 8px; font-size: 14px;
    font-weight: 600; cursor: pointer; transition: all 0.2s;
  }}
  button:disabled {{ opacity: 0.4; cursor: not-allowed; }}
  #startBtn {{
    background: #2563eb; color: white;
  }}
  #startBtn:hover:not(:disabled) {{ background: #1d4ed8; }}
  #stopBtn {{
    background: #dc2626; color: white;
  }}
  #stopBtn:hover:not(:disabled) {{ background: #b91c1c; }}

  .status {{
    font-size: 13px; color: #6b7280; display: flex; align-items: center; gap: 6px;
  }}
  .status .dot {{
    width: 8px; height: 8px; border-radius: 50%; display: inline-block;
  }}
  .dot.ready {{ background: #9ca3af; }}
  .dot.recording {{ background: #dc2626; animation: pulse 1s infinite; }}
  .dot.processing {{ background: #f59e0b; }}
  .dot.done {{ background: #16a34a; }}

  @keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.4; }}
  }}

  .transcript {{
    background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px;
    padding: 16px; max-height: 400px; overflow-y: auto; font-size: 14px;
    line-height: 1.6; white-space: pre-wrap;
  }}
  .transcript .chunk {{
    margin-bottom: 8px; padding: 8px; border-radius: 4px;
  }}
  .transcript .chunk:last-child {{ background: #eff6ff; }}
  .transcript .speaker {{ font-weight: 600; color: #1e40af; }}
  .transcript .empty {{ color: #9ca3af; font-style: italic; }}

  .timer {{
    font-size: 13px; color: #6b7280; font-variant-numeric: tabular-nums;
  }}
</style>
</head>
<body>
  <div class="controls">
    <button id="startBtn" onclick="startRecording()">Start Recording</button>
    <button id="stopBtn" onclick="stopRecording()" disabled>Stop Recording</button>
    <div class="status">
      <span class="dot ready" id="statusDot"></span>
      <span id="statusText">Ready</span>
    </div>
    <div class="timer" id="timer"></div>
  </div>
  <div class="transcript" id="transcript">
    <div class="empty">Click "Start Recording" to begin live transcription...</div>
  </div>

<script>
  const WS_URL = "{ws_url}";
  const SESSION_ID = "{session_id}";
  let mediaRecorder, ws, stream;
  let startTime = 0;
  let timerInterval = null;
  const chunks = {{}};

  function setStatus(text, dotClass) {{
    document.getElementById('statusText').innerText = text;
    const dot = document.getElementById('statusDot');
    dot.className = 'dot ' + dotClass;
  }}

  function updateTimer() {{
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const min = Math.floor(elapsed / 60).toString().padStart(2, '0');
    const sec = (elapsed % 60).toString().padStart(2, '0');
    document.getElementById('timer').innerText = min + ':' + sec;
  }}

  function renderTranscript() {{
    const el = document.getElementById('transcript');
    const keys = Object.keys(chunks).map(Number).sort((a, b) => a - b);
    if (keys.length === 0) {{
      el.innerHTML = '<div class="empty">Listening...</div>';
      return;
    }}
    el.innerHTML = keys.map(k => {{
      const c = chunks[k];
      return '<div class="chunk">' + c.text + '</div>';
    }}).join('');
    el.scrollTop = el.scrollHeight;
  }}

  function sendToStreamlit(data) {{
    // Send data back to Streamlit via postMessage
    try {{
      window.parent.postMessage({{
        type: 'streamlit:setComponentValue',
        value: JSON.stringify(data)
      }}, '*');
    }} catch(e) {{}}
  }}

  function startRecording() {{
    // Create WebSocket connection
    ws = new WebSocket(WS_URL);
    ws.binaryType = 'arraybuffer';

    ws.onopen = () => {{
      setStatus('Connecting...', 'processing');
    }};

    ws.onmessage = (event) => {{
      const msg = JSON.parse(event.data);
      if (msg.type === 'session_ready') {{
        // Now start mic capture
        navigator.mediaDevices.getUserMedia({{
          audio: {{
            channelCount: 1,
            sampleRate: 16000,
            echoCancellation: true,
            noiseSuppression: true,
          }}
        }}).then(s => {{
          stream = s;
          const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
            ? 'audio/webm;codecs=opus' : 'audio/webm';
          mediaRecorder = new MediaRecorder(stream, {{ mimeType }});

          function onChunkData(e) {{
            if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {{
              setStatus('Processing chunk...', 'processing');
              e.data.arrayBuffer().then(buf => ws.send(buf));
            }}
          }}

          function onRecorderStop() {{
            if (!window._stopRequested && ws.readyState === WebSocket.OPEN) {{
              // Create a fresh MediaRecorder so the next chunk gets proper WebM headers
              mediaRecorder = new MediaRecorder(stream, {{ mimeType }});
              mediaRecorder.ondataavailable = onChunkData;
              mediaRecorder.onstop = onRecorderStop;
              mediaRecorder.start();
              setStatus('Recording', 'recording');
            }}
          }}

          mediaRecorder.ondataavailable = onChunkData;
          mediaRecorder.onstop = onRecorderStop;

          window._stopRequested = false;
          mediaRecorder.start();

          // Every 5 seconds, stop the recorder to flush a complete WebM blob,
          // then onstop handler restarts it automatically
          window._chunkInterval = setInterval(() => {{
            if (mediaRecorder && mediaRecorder.state === 'recording') {{
              mediaRecorder.stop();
            }}
          }}, 5000);

          startTime = Date.now();
          timerInterval = setInterval(updateTimer, 1000);
          setStatus('Recording', 'recording');
          document.getElementById('startBtn').disabled = true;
          document.getElementById('stopBtn').disabled = false;
          document.getElementById('transcript').innerHTML = '<div class="empty">Listening...</div>';
        }}).catch(err => {{
          setStatus('Microphone access denied', 'ready');
          ws.close();
        }});

      }} else if (msg.type === 'partial') {{
        chunks[msg.chunk_index] = {{
          text: msg.text,
          speaker: msg.speaker,
        }};
        renderTranscript();
        setStatus('Recording', 'recording');
        sendToStreamlit({{ event: 'partial', chunk_index: msg.chunk_index, text: msg.text, speaker: msg.speaker }});

      }} else if (msg.type === 'final') {{
        setStatus('Complete', 'done');
        sendToStreamlit({{ event: 'final', full_transcript: msg.full_transcript, duration_seconds: msg.duration_seconds, session_id: SESSION_ID }});

      }} else if (msg.type === 'error') {{
        setStatus('Error: ' + msg.message, 'processing');
      }}
    }};

    ws.onclose = () => {{
      if (document.getElementById('statusText').innerText === 'Recording') {{
        setStatus('Disconnected', 'ready');
      }}
    }};

    ws.onerror = () => {{
      setStatus('Connection error', 'ready');
    }};
  }}

  function stopRecording() {{
    window._stopRequested = true;
    if (window._chunkInterval) {{ clearInterval(window._chunkInterval); window._chunkInterval = null; }}
    if (timerInterval) {{ clearInterval(timerInterval); timerInterval = null; }}
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {{
      mediaRecorder.stop();
    }}
    if (stream) {{
      stream.getTracks().forEach(t => t.stop());
    }}
    if (ws && ws.readyState === WebSocket.OPEN) {{
      setStatus('Finalizing...', 'processing');
      ws.send(JSON.stringify({{ type: 'stop' }}));
    }}
    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
  }}
</script>
</body>
</html>
"""


def render_live_transcription_tab():
    """Render the Live Transcription page in the Streamlit demo."""
    st.header("Live Transcription")
    st.caption("Record a patient-doctor conversation in real-time")

    # Initialize session state
    if "live_session_id" not in st.session_state:
        st.session_state.live_session_id = None
    if "live_final_transcript" not in st.session_state:
        st.session_state.live_final_transcript = None
    if "live_duration" not in st.session_state:
        st.session_state.live_duration = 0

    col1, col2 = st.columns([2, 1])

    with col2:
        st.info(
            "**How it works:**\n"
            "1. Click 'Start Recording' and allow mic access\n"
            "2. Speak naturally - transcript appears every ~5 seconds\n"
            "3. Click 'Stop Recording' when done\n"
            "4. Review transcript and click 'Analyze' to process"
        )

    with col1:
        # Create a session if needed
        if st.session_state.live_session_id is None:
            try:
                r = requests.post(f"{API_BASE}/api/transcribe/live/session", timeout=5)
                r.raise_for_status()
                st.session_state.live_session_id = r.json()["session_id"]
            except requests.ConnectionError:
                st.error("Cannot connect to API. Make sure FastAPI is running: `uvicorn app.main:app --reload --port 8000`")
                return
            except Exception as e:
                st.error(f"Could not create session: {e}")
                return

        session_id = st.session_state.live_session_id
        ws_url = f"{WS_BASE}/ws/transcribe/{session_id}"

        # Render the HTML/JS component
        components.html(
            _get_live_transcribe_html(session_id, ws_url),
            height=520,
        )

    # New session button (to start fresh)
    if st.button("New Recording Session"):
        st.session_state.live_session_id = None
        st.session_state.live_final_transcript = None
        st.session_state.live_duration = 0
        st.rerun()

    st.divider()

    # Manual transcript retrieval (fallback if postMessage doesn't work)
    if st.session_state.live_session_id and st.button("Retrieve Transcript"):
        try:
            r = requests.get(
                f"{API_BASE}/api/transcribe/live/{st.session_state.live_session_id}/transcript",
                timeout=30,
            )
            if r.status_code == 200:
                data = r.json()
                st.session_state.live_final_transcript = data["full_transcript"]
                st.session_state.live_duration = data["duration_seconds"]
                st.session_state.live_session_id = None  # Session was cleaned up server-side
                st.rerun()
            elif r.status_code == 404:
                st.warning("Session not found. It may have expired or already been retrieved.")
            else:
                st.error(f"Error: {r.text}")
        except Exception as e:
            st.error(f"Failed to retrieve transcript: {e}")

    # Display final transcript and analyze button
    if st.session_state.live_final_transcript:
        st.success(f"Recording complete ({st.session_state.live_duration:.1f}s)")

        with st.expander("Full Transcript (PHI Redacted)", expanded=True):
            st.text(st.session_state.live_final_transcript)

        st.subheader("Analyze This Transcript")
        visit_date = st.date_input("Visit Date", value=date.today(), key="live_visit_date")
        visit_type = st.selectbox(
            "Visit Type",
            ["routine checkup", "follow-up", "specialist", "urgent care", "telehealth"],
            key="live_visit_type",
        )
        tags = st.text_input("Tags (comma-separated)", placeholder="diabetes, cardiology", key="live_tags")

        if st.button("Analyze Transcript", type="primary"):
            tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
            with st.spinner("Analyzing with LLM (this may take 1-2 minutes)..."):
                try:
                    r = requests.post(f"{API_BASE}/api/analyze", json={
                        "transcript": st.session_state.live_final_transcript,
                        "visit_date": visit_date.isoformat(),
                        "visit_type": visit_type,
                        "tags": tag_list,
                    }, timeout=300)
                    r.raise_for_status()
                    analysis = r.json()
                    st.success(f"Analysis complete! Visit ID: {analysis['visit_id']}")
                    st.session_state["last_visit_id"] = analysis["visit_id"]

                    # Show key results
                    if analysis.get("patient_summary"):
                        ps = analysis["patient_summary"]
                        st.subheader("Visit Summary")
                        st.write(ps.get("visit_summary", ""))

                    st.info("View full details in Visit History.")

                    # Clear transcript for next recording
                    st.session_state.live_final_transcript = None
                    st.session_state.live_duration = 0
                except requests.HTTPError as e:
                    st.error(f"Analysis failed: {e.response.status_code} - {e.response.text}")
                except Exception as e:
                    st.error(f"Analysis failed: {e}")
