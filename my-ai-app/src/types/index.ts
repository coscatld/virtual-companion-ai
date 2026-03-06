/**
 * 基础业务模块 (REST API) 类型定义
 */

export interface RegisterDTO {
    phone: string;
    code: string;
}

export interface CompleteProfileDTO {
    userId: string;
    nickname: string;
    age?: number;
    gender?: '男' | '女';
    healthStatus?: string;
    preferences?: string[];
}

export interface LoginDTO {
    phone: string;
    code?: string;
    password?: string;
}

export interface LoginResponse {
    token: string;
    userId: string;
    userInfo: CompleteProfileDTO;
}

export interface Template {
    id: string;
    name: string;
    coverUrl: string;
    personality: string;
}

/**
 * 简报设置模块
 */
export interface BriefingConfigDTO {
    city: string;
    time: string; // HH:mm 格式
    filePath?: string;
}

/**
 * 统一接口返回泛型
 */
export interface ApiResponse<T = any> {
    code: number;
    message: string;
    data: T;
}
