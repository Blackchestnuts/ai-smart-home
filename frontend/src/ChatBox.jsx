import { useState, useEffect } from 'react'

// 🌟 初始化浏览器语音识别 API (兼容 Chrome 和 Safari)
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;
if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = 'zh-CN'; // 设置中文
  recognition.continuous = false; // 不持续录音，识别完一句就停
  recognition.interimResults = false; // 不要中间结果，只要最终结果
}

function ChatBox({ onDeviceChanged }) {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [isListening, setIsListening] = useState(false) // 🌟 新增：是否正在录音

  // 🌟 新增：语音播报函数
  const speak = (text) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel(); // 取消之前没读完的
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'zh-CN'; // 中文播报
      utterance.rate = 1.0; // 语速
      window.speechSynthesis.speak(utterance);
    }
  }

  // 修改后的发送函数，支持直接传入语音文字
  const sendMessage = async (e, voiceText = null) => {
    if (e) e.preventDefault();
    const textToSend = voiceText || input; // 如果是语音传入，用语音的文本
    if (!textToSend.trim()) return;

    const userMsg = { role: 'user', content: textToSend }
    setMessages(prev => [...prev, userMsg])
    setInput('') // 清空输入框
    setLoading(true)

    try {
      const res = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: textToSend })
      })
      const data = await res.json()
      const aiMsg = { role: 'assistant', content: data.reply }
      setMessages(prev => [...prev, aiMsg])
      
      // 🌟 核心：AI 回复后，自动语音播报！
      speak(data.reply);

      if (data.reply && (data.reply.includes("已为您") || data.reply.includes("开启") || data.reply.includes("关闭"))) {
        onDeviceChanged()
      }
    } catch (err) {
      const errMsg = { role: 'assistant', content: "❌ 连接失败" }
      setMessages(prev => [...prev, errMsg])
    }
    setLoading(false)
  }

  // 🌟 新增：处理麦克风点击
  const toggleListen = () => {
    if (!recognition) {
      alert('您的浏览器不支持语音识别，请使用 Chrome 浏览器！');
      return;
    }

    if (isListening) {
      recognition.stop(); // 如果正在听，点击则停止
    } else {
      recognition.start(); // 开始录音
      setIsListening(true);
    }
  }

  // 🌟 新增：监听语音识别结果
  useEffect(() => {
    if (!recognition) return;

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript; // 拿到识别的文字
      setInput(transcript); // 填入输入框
      sendMessage(null, transcript); // 🌟 直接自动发送！
    };

    recognition.onend = () => {
      setIsListening(false); // 录音结束，恢复状态
    };

    recognition.onerror = (event) => {
      console.error("语音识别错误:", event.error);
      setIsListening(false);
    };

    // 组件卸载时清理
    return () => {
      if (recognition) recognition.stop();
    };
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
        {/* 🌟 新增：麦克风按钮 */}
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