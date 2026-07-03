import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ChatBox from '../ChatBox'

// mock fetch
global.fetch = vi.fn()

// mock EventSource 不存在
global.EventSource = class {
  constructor() {}
  close() {}
}

// mock speechSynthesis
global.SpeechSynthesisUtterance = class {}
global.window.speechSynthesis = { cancel: vi.fn(), speak: vi.fn() }

beforeEach(() => {
  fetch.mockClear()
})

describe('ChatBox', () => {
  it('renders title and input', () => {
    render(<ChatBox onDeviceChanged={vi.fn()} />)
    expect(screen.getByText('🧸 贴心管家')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('试试说：我有点冷')).toBeInTheDocument()
  })

  it('shows user message after submit', async () => {
    fetch.mockResolvedValueOnce({
      json: async () => ({ reply: '好的', device_changed: false }),
    })
    render(<ChatBox onDeviceChanged={vi.fn()} />)

    const input = screen.getByPlaceholderText('试试说：我有点冷')
    fireEvent.change(input, { target: { value: '你好' } })
    fireEvent.click(screen.getByText('发送'))

    await waitFor(() => {
      expect(screen.getByText('你好')).toBeInTheDocument()
      expect(screen.getByText('好的')).toBeInTheDocument()
    })
  })

  it('calls onDeviceChanged when device_changed is true', async () => {
    const onDeviceChanged = vi.fn()
    fetch.mockResolvedValueOnce({
      json: async () => ({ reply: '已开启', device_changed: true }),
    })
    render(<ChatBox onDeviceChanged={onDeviceChanged} />)

    const input = screen.getByPlaceholderText('试试说：我有点冷')
    fireEvent.change(input, { target: { value: '开灯' } })
    fireEvent.click(screen.getByText('发送'))

    await waitFor(() => {
      expect(onDeviceChanged).toHaveBeenCalled()
    })
  })

  it('does NOT call onDeviceChanged when device_changed is false', async () => {
    const onDeviceChanged = vi.fn()
    fetch.mockResolvedValueOnce({
      json: async () => ({ reply: '你好呀', device_changed: false }),
    })
    render(<ChatBox onDeviceChanged={onDeviceChanged} />)

    const input = screen.getByPlaceholderText('试试说：我有点冷')
    fireEvent.change(input, { target: { value: '在吗' } })
    fireEvent.click(screen.getByText('发送'))

    await waitFor(() => {
      expect(screen.getByText('你好呀')).toBeInTheDocument()
    })
    expect(onDeviceChanged).not.toHaveBeenCalled()
  })

  it('shows error message on fetch failure', async () => {
    fetch.mockRejectedValueOnce(new Error('network'))
    render(<ChatBox onDeviceChanged={vi.fn()} />)

    const input = screen.getByPlaceholderText('试试说：我有点冷')
    fireEvent.change(input, { target: { value: 'test' } })
    fireEvent.click(screen.getByText('发送'))

    await waitFor(() => {
      expect(screen.getByText('❌ 连接失败')).toBeInTheDocument()
    })
  })
})
