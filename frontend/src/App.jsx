import { useState, useEffect } from 'react'
import './App.css'

function App() {
  // 1. 定义状态：存放设备列表数据，初始值为空数组
  const [devices, setDevices] = useState([])
  // 2. 定义状态：标记是否正在加载，初始值为 true
  const [loading, setLoading] = useState(true)

  // 3. 副作用函数：组件首次加载时，去后端拉取数据
  useEffect(() => {
    // 请求你后端的接口 (确保后端 uvicorn 还在运行哦！)
    fetch('http://localhost:8000/api/devices')
      .then(res => res.json()) // 把响应体解析成 JSON
      .then(data => {
        setDevices(data)   // 把拿到的数据存进状态里
        setLoading(false)  // 关闭加载状态
      })
      .catch(err => {
        console.error("获取设备失败:", err)
        setLoading(false)
      })
  }, []) // 这里的空数组 [] 极其重要，表示只在组件挂载时运行一次

  // 4. 渲染 UI
  return (
    <div className="app-container">
      <h1>🏠 AI 智能家居控制台</h1>
      
      {/* 如果还在加载，显示 Loading... */}
      {loading ? (
        <p>正在连接家庭中枢...</p>
      ) : (
        /* 加载完成，渲染设备列表 */
        <div className="device-grid">
          {devices.length === 0 ? (
            <p>暂无设备，请先去后端录入。</p>
          ) : (
            devices.map(device => (
              <div key={device.device_id} className="device-card">
                <h3>{device.room} - {device.name}</h3>
                <p>当前状态：{device.is_on ? '🟢 已开启' : '🔴 已关闭'}</p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

export default App