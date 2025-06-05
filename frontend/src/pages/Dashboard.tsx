import React from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Paper,
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import ShoppingBasketIcon from '@mui/icons-material/ShoppingBasket';
import CategoryIcon from '@mui/icons-material/Category';
import BarChartIcon from '@mui/icons-material/BarChart';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const Dashboard: React.FC = () => {
  const { user } = useAuth();

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        <DashboardIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
        Панель управления
      </Typography>

      <Box sx={{ mb: 4 }}>
        <Paper elevation={3} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Добро пожаловать, {user?.username || 'пользователь'}!
          </Typography>
          <Typography variant="body1">
            Используйте WB-Analyzer для анализа товаров и ниш на Wildberries. Выберите один из доступных инструментов ниже:
          </Typography>
        </Paper>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <CardContent sx={{ flexGrow: 1 }}>
              <Typography variant="h5" component="div" gutterBottom>
                <ShoppingBasketIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Анализ товара
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Получите подробный анализ товара по артикулу, включая данные о продажах, позициях в поиске и рекомендации по оптимизации.
              </Typography>
            </CardContent>
            <CardActions>
              <Button
                component={Link}
                to="/product-analysis"
                size="small"
                variant="contained"
                fullWidth
              >
                Перейти к анализу товара
              </Button>
            </CardActions>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <CardContent sx={{ flexGrow: 1 }}>
              <Typography variant="h5" component="div" gutterBottom>
                <CategoryIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Анализ ниши
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Исследуйте конкурентность ниши, распределение цен, популярные бренды и получите рекомендации для работы в выбранной нише.
              </Typography>
            </CardContent>
            <CardActions>
              <Button
                component={Link}
                to="/niche-analysis"
                size="small"
                variant="contained"
                fullWidth
              >
                Перейти к анализу ниши
              </Button>
            </CardActions>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <CardContent sx={{ flexGrow: 1 }}>
              <Typography variant="h5" component="div" gutterBottom>
                <BarChartIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Отслеживание товаров
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Добавляйте товары в список отслеживания, чтобы следить за изменением цен и позиций в поиске.
              </Typography>
            </CardContent>
            <CardActions>
              <Button
                component={Link}
                to="/tracking"
                size="small"
                variant="contained"
                fullWidth
              >
                Перейти к отслеживанию
              </Button>
            </CardActions>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <CardContent sx={{ flexGrow: 1 }}>
              <Typography variant="h5" component="div" gutterBottom>
                Профиль
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Управляйте вашим профилем, подпиской и настройками аккаунта.
              </Typography>
            </CardContent>
            <CardActions>
              <Button
                component={Link}
                to="/profile"
                size="small"
                variant="contained"
                fullWidth
              >
                Перейти в профиль
              </Button>
            </CardActions>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard; 