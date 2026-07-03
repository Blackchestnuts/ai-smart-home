import { useState, useEffect } from 'react'

// 后端 API 地址：开发时由 .env 注入，生产构建时由 docker-compose 注入
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

// 🌟 初始化浏览器语音识别 API (兼容 Chrome 和 Safari)
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;
if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = 'zh-CN';
  recognition.continuous = false;
  recognition.interimResults = false;
}

function ChatBox({ onDeviceChanged }) {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [isListening, setIsListening] = useState(false)

  // 🌟 语音播报函数
  const speak = (text) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'zh-CN';
      utterance.rate = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  }

  // 🌟 优化后的发送函数：支持多轮对话上下文
  const sendMessage = async (e, voiceText = null) => {
    if (e) e.preventDefault();
    const textToSend = voiceText || input;
    if (!textToSend.trim()) return;

    const userMsg = { role: 'user', content: textToSend }
    setMessages(prev => [...prev, userMsg]) // 先把用户消息显示在页面上
    setInput('')
    setLoading(true)

    try {
      // 🌟 核心优化1：提取最近5轮(10条)历史记录发给后端，解决金鱼脑问题
      const history = messages.slice(-10).map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // 🌟 不仅发当前消息，还要发历史记录
        body: JSON.stringify({
          message: textToSend,
          history: history
        })
      })

      const data = await res.json()
      const aiMsg = { role: 'assistant', content: data.reply }
      setMessages(prev => [...prev, aiMsg])

      speak(data.reply);

      // 🌟 核心优化2：只要走了一次 AI 对话，就刷新设备列表
      // （后端 chat.py 暂未返回 device_changed 标志位，这里统一刷新保险）
      if (onDeviceChanged) {
        onDeviceChanged()
      }
    } catch (err) {
      const errMsg = { role: 'assistant', content: "❌ 连接失败" }
      setMessages(prev => [...prev, errMsg])
    }
    setLoading(false)
  }

  // 处理麦克风点击
  const toggleListen = () => {
    if (!recognition) {
      alert('您的浏览器不支持语音识别，请使用 Chrome 浏览器！');
      return;
    }

    if (isListening) {
      recognition.stop();
    } else {
      recognition.start();
      setIsListening(true);
    }
  }

  // 监听语音识别结果
  useEffect(() => {
    if (!recognition) return;

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setInput(transcript);
      sendMessage(null, transcript);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.onerror = (event) => {
      console.error("语音识别错误:", event.error);
      setIsListening(false);
    };

    return () => {
      if (recognition) recognition.stop();
    }
  }, [])

  return (
    <div className="chat-box">
      <h3>🧸 贴心管家</h3>
      <div className="chat-messages">
        {messages.length === 0 && <p style={{color: '#a8a29e', fontSize: '14px', textAlign: 'center', marginTop: '50%'}}>点击下方麦克风，或者输入指令...</p>}
        {messages.map((msg, idx) => (
          <div key={idx} className={`msg ${msg.role}`}>
            {msg.content}
          </div>
        ))}
        {loading && <div className="msg assistant">🧠 思考中...</div>}
      </div>
      <form onSubmit={sendMessage} className="chat-input">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="试试说：我有点冷"
        />
        <button
          type="button"
          className={`mic-btn ${isListening ? 'listening' : ''}`}
          onClick={toggleListen}
          title="语音输入"
        >
          {isListening ? '⏹️' : '🎤'}
        </button>
        <button type="submit">发送</button>
      </form>
    </div>
  )
}

export default ChatBox
