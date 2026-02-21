import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'

// 1. 创建 axios 实例
const request: AxiosInstance = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || '',
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json'
    }
})

// 2. 请求拦截器
request.interceptors.request.use(
    (config: any) => {
        // 使用 Pinia store 中的 token
        const token = localStorage.getItem('token')
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`
        }
        return config
    },
    (error: any) => {
        return Promise.reject(error)
    }
)

// 3. 响应拦截器
request.interceptors.response.use(
    (response: AxiosResponse) => {
        const { data } = response
        // 增加对 code 的兼容，如果是 200 或者数据直接是正常格式
        // 这里基于 Java 后端 Result<T> 结构：code, message, data
        if (data && data.code && data.code !== 200) {
            console.error(data.message || 'Error occurred')
            return Promise.reject(new Error(data.message || 'Error'))
        }
        return data
    },
    (error: any) => {
        if (error.response) {
            switch (error.response.status) {
                case 401:
                    console.warn('Unauthorized. Redirecting to login...')
                    localStorage.removeItem('token')
                    // 可以在这强制刷新或跳转
                    window.location.href = '/login'
                    break
                case 403:
                    console.warn('Forbidden access.')
                    break
                case 500:
                    console.warn('Internal server error.')
                    break
            }
        }
        return Promise.reject(error)
    }
)

export default request
