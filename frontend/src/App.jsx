import { useState, useEffect } from 'react'
import './App.css'
import ChatBox from './ChatBox' // 引入聊天组件

function App() {
  const [devices, setDevices] = useState([])
  const [loading, setLoading] = useState(true)
  const [newName, setNewName] = useState('')
  const [newRoom, setNewRoom] = useState('客厅')

  const fetchDevices = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/devices')
      const data = await res.json()
      setDevices(data)
      setLoading(false)
    } catch (err) {
      console.error("获取设备失败:", err)
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDevices()
  }, [])

  const toggleDevice = async (device) => {
    const apiUrl = device.is_on 
      ? `http://localhost:8000/api/devices/${device.device_id}/off`
      : `http://localhost:8000/api/devices/${device.device_id}/on`
    try {
      const res = await fetch(apiUrl, { method: 'POST' })
      if (res.ok) { fetchDevices() } 
      else {
        const errData = await res.json()
        alert(`操作失败: ${errData.detail}`)
      }
    } catch (err) { console.error("控制设备失败:", err) }
  }

  const handleAddDevice = async (e) => {
    e.preventDefault()
    try {
      const res = await fetch('http://localhost:8000/api/devices', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName, room: newRoom })
      })
      if (res.status === 201) {
        setNewName('')
        fetchDevices()
      }
    } catch (err) { console.error("录入设备失败:", err) }
  }

  const handleDeleteDevice = async (deviceId, deviceName) => {
    if (!window.confirm(`确定要删除设备 [${deviceName}] 吗？`)) return
    try {
      const res = await fetch(`http://localhost:8000/api/devices/${deviceId}`, { method: 'DELETE' })
      if (res.ok) { fetchDevices() } 
      else {
        const errData = await res.json()
        alert(`删除失败: ${errData.detail}`)
      }
    } catch (err) { console.error("删除设备失败:", err) }
  }

  // 传递给 ChatBox 的刷新函数，当 AI 操作了设备后，刷新左侧列表
  const refreshDevices = () => { fetchDevices() }

  return (
    <div className="app-container">
      <h1>🏠 AI 智能家居控制台</h1>
      
      {/* 核心布局：左右分栏 */}
      <div className="main-content">
        
        {/* 左侧：设备管理区 */}
        <div className="device-section">
          <div className="add-device-form">
            <h3>录入新设备</h3>
            <form onSubmit={handleAddDevice}>
              <input 
                type="text" 
                placeholder="设备名称 (如: 落地灯)" 
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                required 
              />
              <select value={newRoom} onChange={(e) => setNewRoom(e.target.value)}>
                <option>客厅</option>
                <option>卧室</option>
                <option>厨房</option>
                <option>书房</option>
              </select>
              <button type="submit">录入</button>
            </form>
          </div>

          <div className="device-grid">
            {loading ? (
              <p>正在连接家庭中枢...</p>
            ) : devices.length === 0 ? (
              <p>暂无设备，请先录入。</p>
            ) : (
              devices.map(device => (
                <div key={device.device_id} className={`device-card ${device.is_on ? 'card-on' : 'card-off'}`}>
                  <h3>{device.room} - {device.name}</h3>
                  <p>状态：{device.is_on ? '🟢 运行中' : '🔴 已关闭'}</p>
                  <div className="btn-group">
                    <button 
                      className={device.is_on ? 'btn-off' : 'btn-on'} 
                      onClick={() => toggleDevice(device)}
                    >
                      {device.is_on ? '一键关闭' : '一键开启'}
                    </button>
                    <button 
                      className="btn-delete" 
                      onClick={() => handleDeleteDevice(device.device_id, device.name)}
                    >
                      移除
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 右侧：AI 聊天区 */}
        <ChatBox onDeviceChanged={refreshDevices} />

      </div>
    </div>
  )
}

export default App