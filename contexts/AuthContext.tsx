import React, { createContext, useContext, useState, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

export interface User {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
  balance: number;
}

export interface AuthCredentials {
  username: string;
  password: string;
}

export interface SignupData {
  email: string;
  username: string;
  password: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: AuthCredentials) => Promise<void>;
  signup: (userData: SignupData) => Promise<void>;
  logout: () => void;
  error: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  // Упрощенная версия для тестирования
  const login = async (credentials: AuthCredentials) => {
    setIsLoading(true);
    // Имитация запроса к API
    setTimeout(() => {
      // Тестовый пользователь
      const mockUser: User = {
        id: 1,
        email: 'test@example.com',
        username: credentials.username,
        is_active: true,
        is_superuser: false,
        balance: 1000
      };
      
      setUser(mockUser);
      localStorage.setItem('token', 'mock-token');
      localStorage.setItem('userId', '1');
      setIsLoading(false);
      navigate('/dashboard');
    }, 1000);
  };

  const signup = async (userData: SignupData) => {
    setIsLoading(true);
    // Имитация запроса к API
    setTimeout(() => {
      const mockUser: User = {
        id: 1,
        email: userData.email,
        username: userData.username,
        is_active: true,
        is_superuser: false,
        balance: 0
      };
      
      setUser(mockUser);
      localStorage.setItem('token', 'mock-token');
      localStorage.setItem('userId', '1');
      setIsLoading(false);
      navigate('/dashboard');
    }, 1000);
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('userId');
    setUser(null);
    navigate('/login');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user || localStorage.getItem('token') !== null,
        isLoading,
        login,
        signup,
        logout,
        error
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}; 