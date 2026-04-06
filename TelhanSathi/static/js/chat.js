document.addEventListener('DOMContentLoaded', () => {
  const chatForm = document.getElementById('chat-form');
  const chatInput = document.getElementById('chat-input');
  const messages = document.getElementById('messages');
  const micBtn = document.getElementById('mic-btn');
  let mediaRecorder = null;
  let audioChunks = [];
  let isRecording = false;

  function appendMessage(text, sender='bot', audio_url=null) {
    const div = document.createElement('div');
    div.className = 'msg ' + sender;
    div.innerHTML = `<div class="bubble">${text}</div>`;
    if (audio_url) {
      const play = document.createElement('button');
      play.className = 'play';
      play.textContent = '🔊';
      play.onclick = () => new Audio(audio_url).play();
      div.appendChild(play);
    }
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;
    appendMessage(text, 'user');
    chatInput.value = '';

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({input_text: text, voice_mode: false})
      });
      const data = await res.json();
      appendMessage(data.text, 'bot', data.audio_url || null);
      // show visual if requested
      if (data.show_visual === 'profit_chart') {
        const visual = document.getElementById('visual');
        visual.style.display = 'block';
      }
    } catch (err) {
      appendMessage('Error contacting bot: ' + err.message, 'bot');
    }
  });

  // Mic button placeholder: in future hook MediaRecorder
  if (micBtn) micBtn.addEventListener('click', async () => {
    // Toggle recording
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      appendMessage('Voice not supported in this browser.', 'bot');
      return;
    }

    if (!isRecording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
        mediaRecorder.onstop = async () => {
          const blob = new Blob(audioChunks, { type: 'audio/webm' });
          // show temporary message
          appendMessage('Uploading audio for transcription...', 'bot');

          const fd = new FormData();
          fd.append('audio', blob, 'recording.webm');

          try {
            const uploadRes = await fetch('/api/audio_upload', { method: 'POST', body: fd });
            const uploadData = await uploadRes.json();
            const transcript = uploadData.transcript || '';

            // Show user's transcribed message
            appendMessage(transcript || '(no transcript)', 'user');

            // Send transcript to chat API
            const chatRes = await fetch('/api/chat', {
              method: 'POST',
              headers: {'Content-Type':'application/json'},
              body: JSON.stringify({ input_text: transcript, voice_mode: true })
            });
            const chatData = await chatRes.json();
            appendMessage(chatData.text, 'bot', chatData.audio_url || null);
            if (chatData.show_visual === 'profit_chart') {
              const visual = document.getElementById('visual');
              visual.style.display = 'block';
            }
          } catch (err) {
            appendMessage('Audio upload or transcription failed: ' + err.message, 'bot');
          }
        };

        mediaRecorder.start();
        isRecording = true;
        micBtn.textContent = '⏺️';
        appendMessage('Recording... Tap mic again to stop.', 'bot');
      } catch (err) {
        appendMessage('Could not start microphone: ' + err.message, 'bot');
      }
    } else {
      // stop
      if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
      isRecording = false;
      micBtn.textContent = '🎤';
    }
  });
});
