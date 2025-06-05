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
  Divider,
} from '@mui/material';
import CategoryIcon from '@mui/icons-material/Category';
import nicheService, { NicheAnalysisResult } from '../services/nicheService';

export const NicheAnalysis: React.FC = () => {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<NicheAnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    
    if (!query) {
      setError('Пожалуйста, введите поисковый запрос');
      return;
    }
    
    try {
      setIsLoading(true);
      // Моковые данные для тестирования
      const mockData: NicheAnalysisResult = {
        niche_name: query,
        total_products: 1250,
        avg_price: 2499,
        price_range: { min: 999, max: 5999 },
        top_brands: [
          { name: 'Бренд 1', count: 350 },
          { name: 'Бренд 2', count: 280 },
          { name: 'Бренд 3', count: 210 },
        ],
        recommendations: [
          'Рекомендация 1 для ниши',
          'Рекомендация 2 для ниши',
          'Рекомендация 3 для ниши',
        ]
      };
      
      setResult(mockData);
    } catch (err: any) {
      console.error('Error analyzing niche:', err);
      setError(err.message || 'Ошибка при анализе ниши');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        <CategoryIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
        Анализ ниши на Wildberries
      </Typography>
      
      <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          Введите поисковый запрос для анализа ниши
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
                label="Поисковый запрос"
                variant="outlined"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Например: женские платья"
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
              Результаты анализа ниши: {result.niche_name}
            </Typography>
            
            <Grid container spacing={3} sx={{ mt: 1 }}>
              <Grid item xs={12} md={4}>
                <Typography variant="body1" fontWeight="bold">
                  Всего товаров:
                </Typography>
                <Typography variant="h6">
                  {result.total_products.toLocaleString()}
                </Typography>
              </Grid>
              
              <Grid item xs={12} md={4}>
                <Typography variant="body1" fontWeight="bold">
                  Средняя цена:
                </Typography>
                <Typography variant="h6">
                  {result.avg_price.toLocaleString()} ₽
                </Typography>
              </Grid>
              
              <Grid item xs={12} md={4}>
                <Typography variant="body1" fontWeight="bold">
                  Диапазон цен:
                </Typography>
                <Typography variant="h6">
                  {result.price_range.min.toLocaleString()} - {result.price_range.max.toLocaleString()} ₽
                </Typography>
              </Grid>
            </Grid>
            
            <Divider sx={{ my: 3 }} />
            
            <Typography variant="h6" gutterBottom>
              Топ брендов:
            </Typography>
            
            {result.top_brands.map((brand) => (
              <Box key={brand.name} sx={{ mb: 1 }}>
                <Typography variant="body1">
                  {brand.name}: {brand.count} товаров ({((brand.count / result.total_products) * 100).toFixed(1)}%)
                </Typography>
              </Box>
            ))}
            
            {result.recommendations && (
              <>
                <Divider sx={{ my: 3 }} />
                
                <Typography variant="h6" gutterBottom>
                  Рекомендации:
                </Typography>
                
                {result.recommendations.map((rec, index) => (
                  <Typography key={index} variant="body1" sx={{ mb: 1 }}>
                    • {rec}
                  </Typography>
                ))}
              </>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  );
}; 