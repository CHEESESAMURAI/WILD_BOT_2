import React from 'react';
import { BrowserRouter as Router, Switch, Route, Redirect } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { AuthProvider } from './contexts/AuthContext';
import { MainLayout } from './layouts/MainLayout';
import { Login } from './pages/Login';
import { Signup } from './pages/Signup';
import { ProductAnalysis } from './pages/ProductAnalysis';
import { NicheAnalysis } from './pages/NicheAnalysis';
import Dashboard from './pages/Dashboard';
import Tracking from './pages/Tracking';
import Profile from './pages/Profile';
import ComingSoonPage from './pages/ComingSoonPage';
import './App.css';

// Создаем тему приложения
const theme = createTheme({
  palette: {
    primary: {
      main: '#2196f3',
    },
    secondary: {
      main: '#f50057',
    },
  },
});

// Компонент приватного маршрута
const PrivateRoute = ({ children, ...rest }: { children: React.ReactNode; path: string; exact?: boolean }) => {
  const isAuthenticated = localStorage.getItem('token') !== null;
  return (
    <Route
      {...rest}
      render={({ location }) =>
        isAuthenticated ? (
          children
        ) : (
          <Redirect
            to={{
              pathname: "/login",
              state: { from: location }
            }}
          />
        )
      }
    />
  );
};

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <AuthProvider>
          <Switch>
            <Route path="/login">
              <Login />
            </Route>
            <Route path="/signup">
              <Signup />
            </Route>
            
            <MainLayout>
              <Switch>
                <Route exact path="/">
                  <Redirect to="/dashboard" />
                </Route>
                
                <PrivateRoute path="/dashboard" exact>
                  <Dashboard />
                </PrivateRoute>
                
                <PrivateRoute path="/product-analysis" exact>
                  <ProductAnalysis />
                </PrivateRoute>
                
                <PrivateRoute path="/niche-analysis" exact>
                  <NicheAnalysis />
                </PrivateRoute>
                
                <PrivateRoute path="/tracking" exact>
                  <Tracking />
                </PrivateRoute>
                
                <PrivateRoute path="/profile" exact>
                  <Profile />
                </PrivateRoute>
                
                <PrivateRoute path="/query-oracle" exact>
                  <ComingSoonPage title="Оракул запросов" />
                </PrivateRoute>
                
                {/* Новые маршруты для функций в разработке */}
                <PrivateRoute path="/brand-analysis" exact>
                  <ComingSoonPage title="Анализ бренда" />
                </PrivateRoute>
                
                <PrivateRoute path="/supplier-analysis" exact>
                  <ComingSoonPage title="Анализ поставщика" />
                </PrivateRoute>
                
                <PrivateRoute path="/category-analysis" exact>
                  <ComingSoonPage title="Анализ категорий" />
                </PrivateRoute>
                
                <PrivateRoute path="/item-analysis" exact>
                  <ComingSoonPage title="Анализ предметов" />
                </PrivateRoute>
                
                <PrivateRoute path="/visual-analysis" exact>
                  <ComingSoonPage title="Анализ внешки" />
                </PrivateRoute>
                
                <PrivateRoute path="/ad-monitoring" exact>
                  <ComingSoonPage title="Мониторинг рекламы" />
                </PrivateRoute>
                
                <PrivateRoute path="/ai-assistant" exact>
                  <ComingSoonPage title="Помощь с нейронкой" />
                </PrivateRoute>
                
                <PrivateRoute path="/supply-plan" exact>
                  <ComingSoonPage title="План поставок" />
                </PrivateRoute>
                
                <PrivateRoute path="/global-search" exact>
                  <ComingSoonPage title="Глобальный поиск" />
                </PrivateRoute>
                
                <Route path="*">
                  <Redirect to="/" />
                </Route>
              </Switch>
            </MainLayout>
          </Switch>
        </AuthProvider>
      </Router>
    </ThemeProvider>
  );
}

export default App; 