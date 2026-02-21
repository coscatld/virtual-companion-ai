import request from './request'

// Mock 接口类型定义
export interface Agent {
    id: string
    name: string
    model: string
    status: 'running' | 'stopped'
    updatedAt: string
}

/**
 * 获取 AI Agent 列表（Mock 延迟 1秒）
 */
export const fetchAgents = async (): Promise<Agent[]> => {
    // 真实情况使用 axios：
    // return request.get<any, Agent[]>('/agents')

    return new Promise((resolve) => {
        setTimeout(() => {
            resolve([
                { id: 'ag-01', name: 'Chat Support Bot', model: 'gpt-4o', status: 'running', updatedAt: '2025-10-12 10:30' },
                { id: 'ag-02', name: 'Data Analyst Agent', model: 'claude-3.5-sonnet', status: 'stopped', updatedAt: '2025-10-10 16:45' },
                { id: 'ag-03', name: 'Virtual Girlfriend', model: 'qwen-2.5-7b', status: 'running', updatedAt: '2025-10-12 11:20' }
            ])
        }, 1000)
    })
}

/**
 * 模拟删除 Agent
 */
export const deleteAgent = async (id: string): Promise<boolean> => {
    return new Promise((resolve) => {
        setTimeout(() => resolve(true), 500)
    })
}
