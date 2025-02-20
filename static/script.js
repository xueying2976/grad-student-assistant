document.getElementById("send-btn").addEventListener("click", sendMessage);

var lastBotMessage = ""

function sendMessage() {
  const input = document.getElementById("user-input");
  const message = input.value.trim();

  if (message) {
    addMessage(message, "user-message");
    input.value = "";

    fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: message,
      }),
    })
      .then(response => response.json())
      .then(data => addMessage(data.text, "bot-message"))
      .catch(error => console.error("Error:", error));
  }
}

function addMessage(text, className) {
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${className}`;
  if (className === "user-message") {
    messageDiv.textContent = text;
  } else {
    console.log(text)
    messageDiv.innerHTML = marked.parse(text)
  }
  document.getElementById("messages").appendChild(messageDiv);
  const chatWindow = document.getElementById("chat-window");
  chatWindow.scrollTop = chatWindow.scrollHeight;

  return false
}
