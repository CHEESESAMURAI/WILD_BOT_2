import React, { useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Grid,
  CircularProgress,
  Card,
  CardContent,
  Alert,
} from '@mui/material';
import ShoppingBasketIcon from '@mui/icons-material/ShoppingBasket';
import productService, { ProductAnalysisResult } from '../services/productService';
import { useAuth } from '../contexts/AuthContext';

export const ProductAnalysis: React.FC = () => {
  const [article, setArticle] = useState('');
  const [result, setResult] = useState<ProductAnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth();

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
      setError(err.message || 'Ошибка при анализе товара');
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
      alert(err.message || 'Ошибка при добавлении товара в отслеживаемые');
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
        <Card>
          <CardContent>
            <Typography variant="h5" gutterBottom>
              {result.name}
            </Typography>
            <Typography variant="body1">
              Артикул: {result.article}
            </Typography>
            <Typography variant="body1">
              Цена: {result.price} ₽
            </Typography>
            {result.brand && (
              <Typography variant="body1">
                Бренд: {result.brand}
              </Typography>
            )}
            {result.rating && (
              <Typography variant="body1">
                Рейтинг: {result.rating}
              </Typography>
            )}
            {result.reviews_count && (
              <Typography variant="body1">
                Отзывы: {result.reviews_count}
              </Typography>
            )}
            
            <Button 
              variant="contained" 
              onClick={handleTrackProduct}
              sx={{ mt: 2 }}
            >
              Отслеживать товар
            </Button>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}; 