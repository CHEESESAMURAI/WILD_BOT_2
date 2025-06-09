import React, { useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Grid,
  CircularProgress,
  Divider,
  Card,
  CardContent,
  CardMedia,
  List,
  ListItem,
  ListItemText,
  Alert,
  Tabs,
  Tab,
} from '@mui/material';
import ShoppingBasketIcon from '@mui/icons-material/ShoppingBasket';
import productService, { ProductAnalysisResult } from '../services/productService';
import { useAuth } from '../contexts/AuthContext';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`simple-tabpanel-${index}`}
      aria-labelledby={`simple-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export const ProductAnalysis: React.FC = () => {
  const [article, setArticle] = useState('');
  const [result, setResult] = useState<ProductAnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const { user } = useAuth();

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    
    if (!article) {
      setError('Пожалуйста, введите артикул товара');
      return;
    }
    
    try {
      setIsLoading(true);
      const data = await productService.analyzeProduct(article);
      setResult(data);
    } catch (err: any) {
      console.error('Error analyzing product:', err);
      setError(err.response?.data?.detail || 'Ошибка при анализе товара');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTrackProduct = async () => {
    if (!result || !user) return;
    
    try {
      await productService.trackProduct({
        article: result.article,
        name: result.name,
        price: result.price,
        user_id: user.id
      });
      alert('Товар добавлен в отслеживаемые');
    } catch (err: any) {
      console.error('Error tracking product:', err);
      alert(err.response?.data?.detail || 'Ошибка при добавлении товара в отслеживаемые');
    }
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        <ShoppingBasketIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
        Анализ товара на Wildberries
      </Typography>
      
      <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          Введите артикул товара для анализа
        </Typography>
        
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        
        <Box component="form" onSubmit={handleSubmit}>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={9}>
              <TextField
                fullWidth
                label="Артикул товара"
                variant="outlined"
                value={article}
                onChange={(e) => setArticle(e.target.value)}
                placeholder="Например: 12345678"
              />
            </Grid>
            <Grid item xs={12} sm={3}>
              <Button
                fullWidth
                variant="contained"
                type="submit"
                disabled={isLoading}
                sx={{ height: '100%' }}
              >
                {isLoading ? <CircularProgress size={24} /> : 'Анализировать'}
              </Button>
            </Grid>
          </Grid>
        </Box>
      </Paper>
      
      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      )}
      
      {result && !isLoading && (
        <Box>
          <Card sx={{ mb: 4 }}>
            <Grid container>
              <Grid item xs={12} md={4}>
                <CardMedia
                  component="img"
                  height="300"
                  image={`https://picsum.photos/seed/${result.article}/300/300`} // Заглушка, в реальности нужно использовать реальное изображение
                  alt={result.name}
                />
              </Grid>
              <Grid item xs={12} md={8}>
                <CardContent>
                  <Typography variant="h5" component="div" gutterBottom>
                    {result.name}
                  </Typography>
                  <Typography variant="subtitle1" color="text.secondary" gutterBottom>
                    Артикул: {result.article}
                  </Typography>
                  <Typography variant="subtitle1" gutterBottom>
                    Бренд: {result.brand || 'Не указан'}
                  </Typography>
                  <Typography variant="h6" color="primary" gutterBottom>
                    Цена: {result.price.toLocaleString()} ₽
                  </Typography>
                  <Typography variant="body2" gutterBottom>
                    Рейтинг: {result.rating || 'Нет данных'} / 5
                  </Typography>
                  <Typography variant="body2" gutterBottom>
                    Отзывов: {result.reviews_count || 0}
                  </Typography>
                  
                  <Button
                    variant="outlined"
                    color="primary"
                    onClick={handleTrackProduct}
                    sx={{ mt: 2 }}
                  >
                    Отслеживать товар
                  </Button>
                </CardContent>
              </Grid>
            </Grid>
          </Card>
          
          <Box sx={{ width: '100%' }}>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs value={tabValue} onChange={handleTabChange} aria-label="basic tabs example">
                <Tab label="Рекомендации" />
                <Tab label="Графики" />
                <Tab label="Данные о продажах" />
              </Tabs>
            </Box>
            
            <TabPanel value={tabValue} index={0}>
              <Typography variant="h6" gutterBottom>
                Рекомендации по товару:
              </Typography>
              {result.recommendations && result.recommendations.length > 0 ? (
                <List>
                  {result.recommendations.map((rec, index) => (
                    <ListItem key={index} divider={index < result.recommendations!.length - 1}>
                      <ListItemText primary={rec} />
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography>Нет рекомендаций для данного товара</Typography>
              )}
            </TabPanel>
            
            <TabPanel value={tabValue} index={1}>
              <Typography variant="h6" gutterBottom>
                Графики:
              </Typography>
              {result.charts && result.charts.length > 0 ? (
                <Grid container spacing={2}>
                  {result.charts.map((chart, index) => (
                    <Grid item xs={12} md={6} key={index}>
                      <img 
                        src={`data:image/png;base64,${chart}`} 
                        alt={`График ${index+1}`}
                        style={{ width: '100%', height: 'auto' }}
                      />
                    </Grid>
                  ))}
                </Grid>
              ) : (
                <Typography>Нет графиков для данного товара</Typography>
              )}
            </TabPanel>
            
            <TabPanel value={tabValue} index={2}>
              <Typography variant="h6" gutterBottom>
                Данные о продажах:
              </Typography>
              {result.sales_data ? (
                <pre>{JSON.stringify(result.sales_data, null, 2)}</pre>
              ) : (
                <Typography>Нет данных о продажах</Typography>
              )}
            </TabPanel>
          </Box>
        </Box>
      )}
    </Box>
  );
}; 