import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [devices, setDevices] = useState([])
  const [loading, setLoading] = useState(true)
  
  // 新增：表单输入状态
  const [newName, setNewName] = useState('')
  const [newRoom, setNewRoom] = useState('客厅')

  // 获取设备列表的函数（抽离出来复用）
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

  // 组件挂载时拉取数据
  useEffect(() => {
    fetchDevices()
  }, [])

  // 🌟 新增功能1：开关设备
  const toggleDevice = async (device) => {
    // 判断当前状态，决定调用开还是关的接口
    const apiUrl = device.is_on 
      ? `http://localhost:8000/api/devices/${device.device_id}/off`
      : `http://localhost:8000/api/devices/${device.device_id}/on`

    try {
      const res = await fetch(apiUrl, { method: 'POST' })
      if (res.ok) {
        // 请求成功后，重新拉取列表，刷新页面状态
        fetchDevices() 
      } else {
        const errData = await res.json()
        alert(`操作失败: ${errData.detail}`) // 弹出后端返回的 400 错误（如重复开启）
      }
    } catch (err) {
      console.error("控制设备失败:", err)
    }
  }

  // 🌟 新增功能2：录入新设备
  const handleAddDevice = async (e) => {
    e.preventDefault() // 阻止表单默认提交刷新页面
    try {
      const res = await fetch('http://localhost:8000/api/devices', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName, room: newRoom })
      })
      if (res.status === 201) {
        setNewName('') // 清空输入框
        fetchDevices() // 重新拉取列表，展示新设备
      }
    } catch (err) {
      console.error("录入设备失败:", err)
    }
  }

    // 🌟 新增功能3：删除设备
  const handleDeleteDevice = async (deviceId, deviceName) => {
    // 弹窗二次确认，防误触！
    if (!window.confirm(`确定要删除设备 [${deviceName}] 吗？此操作不可撤销！`)) {
      return; // 用户点了取消，直接返回，什么都不做
    }

    try {
      const res = await fetch(`http://localhost:8000/api/devices/${deviceId}`, {
        method: 'DELETE'
      })
      if (res.ok) {
        fetchDevices(); // 删除成功，重新拉取列表刷新页面
      } else {
        const errData = await res.json()
        alert(`删除失败: ${errData.detail}`)
      }
    } catch (err) {
      console.error("删除设备失败:", err)
    }
  }

  return (
    <div className="app-container">
      <h1>🏠 AI 智能家居控制台</h1>

      {/* 录入设备表单 */}
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
            <option>主卧</option>
            <option>次卧</option>
            <option>厨房</option>
            <option>书房</option>
            <option>阳台</option>
            <option>厕所</option>
          </select>
          <button type="submit">录入</button>
        </form>
      </div>

      {/* 设备列表 */}
      {loading ? (
        <p>正在连接家庭中枢...</p>
      ) : (
        <div className="device-grid">
          {devices.length === 0 ? (
            <p>暂无设备，请先录入。</p>
          ) : (
            devices.map(device => (
              <div key={device.device_id} className={`device-card ${device.is_on ? 'card-on' : 'card-off'}`}>
                <h3>{device.room} - {device.name}</h3>
                <p>状态：{device.is_on ? '🟢 运行中' : '🔴 已关闭'}</p>
                <button 
                  className={device.is_on ? 'btn-off' : 'btn-on'} 
                  onClick={() => toggleDevice(device)}
                >
                  {device.is_on ? '一键关闭' : '一键开启'}
                </button>
                 {/* 🌟 新增：删除按钮 */}
                <button 
                  className="btn-delete" 
                  onClick={() => handleDeleteDevice(device.device_id, device.name)}
                >
                  移除设备
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

export default App