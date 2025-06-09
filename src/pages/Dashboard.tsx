import React from 'react';
import {
  Box,
  Typography,
  Grid as MuiGrid,
  Card,
  CardContent,
  Button,
  Paper,
  Divider,
  Avatar,
  Chip,
  IconButton,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';

// Создаем компоненты-обертки для Grid для решения проблем с типизацией
const Grid = MuiGrid;
const GridItem = (props: any) => <MuiGrid item {...props} />;

// Иконки
import PersonIcon from '@mui/icons-material/Person';
import ShoppingBasketIcon from '@mui/icons-material/ShoppingBasket';
import CategoryIcon from '@mui/icons-material/Category';
import SearchIcon from '@mui/icons-material/Search';
import MonetizationOnIcon from '@mui/icons-material/MonetizationOn';
import StoreIcon from '@mui/icons-material/Store';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import AssessmentIcon from '@mui/icons-material/Assessment';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import AutorenewIcon from '@mui/icons-material/Autorenew';
import GradeIcon from '@mui/icons-material/Grade';
import EventNoteIcon from '@mui/icons-material/EventNote';
import AdsClickIcon from '@mui/icons-material/AdsClick';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const Dashboard: React.FC = () => {
  const { user } = useAuth();

  const actionItems = [
    {
      title: "Анализ артикула", 
      icon: <ShoppingBasketIcon />, 
      color: "#1976d2", 
      path: "/product-analysis"
    },
    {
      title: "Анализ бренда", 
      icon: <GradeIcon />, 
      color: "#9c27b0", 
      path: "/brand-analysis"
    },
    {
      title: "Анализ поставщика", 
      icon: <StoreIcon />, 
      color: "#2e7d32", 
      path: "/supplier-analysis"
    },
    {
      title: "Анализ категорий", 
      icon: <CategoryIcon />, 
      color: "#ed6c02", 
      path: "/category-analysis"
    },
    {
      title: "Анализ предметов", 
      icon: <AssessmentIcon />, 
      color: "#d32f2f", 
      path: "/item-analysis"
    },
    {
      title: "Ниши и тренды", 
      icon: <TrendingUpIcon />, 
      color: "#0288d1", 
      path: "/niche-analysis"
    },
    {
      title: "Анализ внешки", 
      icon: <VisibilityIcon />, 
      color: "#7b1fa2", 
      path: "/visual-analysis"
    },
    {
      title: "Мониторинг рекламы", 
      icon: <AdsClickIcon />, 
      color: "#1565c0", 
      path: "/ad-monitoring"
    },
    {
      title: "Помощь с нейронкой", 
      icon: <SmartToyIcon />, 
      color: "#00796b", 
      path: "/ai-assistant"
    },
    {
      title: "План поставок", 
      icon: <EventNoteIcon />, 
      color: "#bf360c", 
      path: "/supply-plan"
    },
    {
      title: "Отслеживание", 
      icon: <AutorenewIcon />, 
      color: "#2e7d32", 
      path: "/tracking"
    },
    {
      title: "Глобальный поиск", 
      icon: <SearchIcon />, 
      color: "#0288d1", 
      path: "/global-search"
    }
  ];

  return (
    <Box>
      <Typography variant="h3" component="h1" gutterBottom align="center" sx={{ fontWeight: 500, mb: 4 }}>
        Личный кабинет
      </Typography>

      <Grid container spacing={3}>
        {/* Блок профиля */}
        <GridItem xs={12} md={4} lg={3}>
          <Paper elevation={2} sx={{ p: 3, height: '100%' }}>
            <Typography variant="h5" component="h2" gutterBottom sx={{ fontWeight: 500 }}>
              Ваш профиль
            </Typography>
            <Divider sx={{ mb: 2 }} />
            
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Avatar sx={{ bgcolor: '#1976d2', mr: 2 }}>
                <PersonIcon />
              </Avatar>
              <Typography variant="body1" sx={{ fontWeight: 500 }}>
                {user?.username || 'Пользователь'}
              </Typography>
            </Box>
            
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">
                Баланс
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <MonetizationOnIcon sx={{ color: 'success.main', mr: 1 }} />
                <Typography>
                  {user?.balance?.toLocaleString() || '0'} ₽
                </Typography>
              </Box>
            </Box>
            
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">
                Подписка
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography>free</Typography>
                <Chip label="Активна" color="success" size="small" />
              </Box>
            </Box>
            
            <Button 
              variant="outlined" 
              fullWidth 
              component={Link} 
              to="/profile" 
              sx={{ mt: 1 }}
            >
              УПРАВЛЕНИЕ ПРОФИЛЕМ
            </Button>
          </Paper>
        </GridItem>

        {/* Основной контент */}
        <GridItem xs={12} md={8} lg={9}>
          {/* Быстрые действия */}
          <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
            <Typography variant="h5" component="h2" gutterBottom sx={{ fontWeight: 500 }}>
              Быстрые действия
            </Typography>
            <Divider sx={{ mb: 3 }} />
            
            <Grid container spacing={2}>
              {actionItems.slice(0, 9).map((item, index) => (
                <GridItem xs={12} sm={6} md={4} key={index}>
                  <Button
                    variant="contained"
                    component={Link}
                    to={item.path}
                    fullWidth
                    startIcon={item.icon}
                    sx={{ 
                      py: 2, 
                      bgcolor: item.color, 
                      '&:hover': { bgcolor: item.color, filter: 'brightness(90%)' },
                      justifyContent: 'flex-start',
                      mb: 1
                    }}
                  >
                    {item.title}
                  </Button>
                </GridItem>
              ))}
              
              {actionItems.slice(9).map((item, index) => (
                <GridItem xs={12} sm={6} md={4} key={index + 9}>
                  <Button
                    variant="contained"
                    component={Link}
                    to={item.path}
                    fullWidth
                    startIcon={item.icon}
                    sx={{ 
                      py: 2, 
                      bgcolor: item.color, 
                      '&:hover': { bgcolor: item.color, filter: 'brightness(90%)' },
                      justifyContent: 'flex-start',
                      mb: 1 
                    }}
                  >
                    {item.title}
                  </Button>
                </GridItem>
              ))}
            </Grid>
          </Paper>

          {/* Отслеживаемые товары */}
          <Paper elevation={2} sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="h5" component="h2" sx={{ fontWeight: 500 }}>
                Отслеживаемые товары
              </Typography>
              <Button 
                variant="outlined" 
                size="small" 
                component={Link} 
                to="/tracking"
              >
                СМОТРЕТЬ ВСЕ
              </Button>
            </Box>
            <Divider sx={{ mb: 3 }} />
            
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                У вас пока нет отслеживаемых товаров. 
                <Link to="/product-analysis" style={{ marginLeft: 8, textDecoration: 'none' }}>
                  Добавить товар
                </Link>
              </Typography>
            </Box>
          </Paper>
        </GridItem>
      </Grid>
    </Box>
  );
};

export default Dashboard; 