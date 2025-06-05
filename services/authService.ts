import api from './api';

export interface AuthCredentials {
  username: string;
  password: string;
}

export interface SignupData {
  email: string;
  username: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
  balance: number;
}

// Для тестирования - возвращает моковые данные
const login = async (credentials: AuthCredentials): Promise<AuthResponse> => {
  // В реальном приложении здесь был бы запрос к API
  return {
    access_token: 'mock-token',
    token_type: 'bearer'
  };
};

const signup = async (userData: SignupData): Promise<User> => {
  // В реальном приложении здесь был бы запрос к API
  return {
    id: 1,
    email: userData.email,
    username: userData.username,
    is_active: true,
    is_superuser: false,
    balance: 0
  };
};

const getCurrentUser = async (userId: number): Promise<User> => {
  // В реальном приложении здесь был бы запрос к API
  return {
    id: userId,
    email: 'test@example.com',
    username: 'testuser',
    is_active: true,
    is_superuser: false,
    balance: 1000
  };
};

const authService = {
  login,
  signup,
  getCurrentUser,
};

export default authService; 