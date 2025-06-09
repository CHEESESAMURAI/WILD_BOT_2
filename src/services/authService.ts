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

const login = async (credentials: AuthCredentials): Promise<AuthResponse> => {
  const formData = new FormData();
  formData.append('username', credentials.username);
  formData.append('password', credentials.password);
  
  const response = await api.post<AuthResponse>('/auth/login/access-token', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  return response.data;
};

const signup = async (userData: SignupData): Promise<User> => {
  const response = await api.post<User>('/auth/signup', userData);
  return response.data;
};

const getCurrentUser = async (userId: number): Promise<User> => {
  const response = await api.get<User>(`/users/me?user_id=${userId}`);
  return response.data;
};

const authService = {
  login,
  signup,
  getCurrentUser,
};

export default authService; 