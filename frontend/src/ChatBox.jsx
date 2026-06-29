import { useState } from 'react'

function ChatBox({ onDeviceChanged }) {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!input.trim()) return

    // 显示用户消息
    const userMsg = { role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input })
      })
      const data = await res.json()
      
      // 显示 AI 回复
      const aiMsg = { role: 'assistant', content: data.reply }
      setMessages(prev => [...prev, aiMsg])
      
      // 如果 AI 操作了设备，通知父组件刷新设备列表
      if (data.reply && (data.reply.includes("已为您") || data.reply.includes("开启") || data.reply.includes("关闭"))) {
        onDeviceChanged()
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: "❌ 连接AI助手失败，请检查后端服务" }])
    }
    setLoading(false)
  }

  return (
    <div className="chat-box">
      <h3>🤖 AI 管家</h3>
      <div className="chat-messages">
        {messages.length === 0 && <p style={{color: '#999', fontSize: '14px'}}>试试对我说："我有点冷" 或 "把台灯关了"</p>}
        {messages.map((msg, idx) => (
          <div key={idx} className={`msg ${msg.role}`}>
            {msg.content}
          </div>
        ))}
        {loading && <div className="msg assistant">🤔 思考中...</div>}
      </div>
      <form onSubmit={sendMessage} className="chat-input">
        <input 
          value={input} 
          onChange={(e) => setInput(e.target.value)} 
          placeholder="输入指令..." 
        />
        <button type="submit">发送</button>
      </form>
    </div>
  )
}

export default ChatBox