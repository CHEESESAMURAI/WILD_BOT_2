import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import authService, { User, AuthCredentials, SignupData } from '../services/authService';
import { useNavigate } from 'react-router-dom';

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

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const checkAuth = async () => {
      setIsLoading(true);
      try {
        const token = localStorage.getItem('token');
        const userId = localStorage.getItem('userId');
        
        if (token && userId) {
          const userData = await authService.getCurrentUser(parseInt(userId, 10));
          setUser(userData);
        }
      } catch (err) {
        console.error('Authentication error:', err);
        localStorage.removeItem('token');
        localStorage.removeItem('userId');
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (credentials: AuthCredentials) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await authService.login(credentials);
      localStorage.setItem('token', response.access_token);
      
      // Извлекаем ID пользователя из токена (упрощенно)
      // В реальном приложении лучше использовать JWT декодирование
      const userId = parseUserIdFromToken(response.access_token);
      localStorage.setItem('userId', userId.toString());
      
      const userData = await authService.getCurrentUser(userId);
      setUser(userData);
      
      navigate('/dashboard');
    } catch (err: any) {
      console.error('Login error:', err);
      setError(err.response?.data?.detail || 'Ошибка при входе');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (userData: SignupData) => {
    setIsLoading(true);
    setError(null);
    
    try {
      await authService.signup(userData);
      await login({
        username: userData.username,
        password: userData.password
      });
    } catch (err: any) {
      console.error('Signup error:', err);
      setError(err.response?.data?.detail || 'Ошибка при регистрации');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('userId');
    setUser(null);
    navigate('/login');
  };

  // Временная функция для извлечения ID пользователя из токена
  const parseUserIdFromToken = (token: string): number => {
    try {
      // В реальном приложении здесь должно быть JWT декодирование
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const payload = JSON.parse(window.atob(base64));
      return payload.sub;
    } catch (err) {
      console.error('Error parsing token:', err);
      return 0;
    }
  };

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    signup,
    logout,
    error
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}; 