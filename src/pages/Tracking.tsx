import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  CircularProgress,
  Alert,
  Card,
  CardContent,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import BarChartIcon from '@mui/icons-material/BarChart';
import productService, { Product } from '../services/productService';
import { useAuth } from '../contexts/AuthContext';

const Tracking: React.FC = () => {
  const [trackedProducts, setTrackedProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth();

  useEffect(() => {
    const fetchTrackedProducts = async () => {
      if (!user) return;
      
      try {
        setIsLoading(true);
        const products = await productService.getTrackedProducts(user.id);
        setTrackedProducts(products);
      } catch (err: any) {
        console.error('Error fetching tracked products:', err);
        setError(err.response?.data?.detail || 'Ошибка при загрузке отслеживаемых товаров');
      } finally {
        setIsLoading(false);
      }
    };

    fetchTrackedProducts();
  }, [user]);

  const handleDeleteTrackedProduct = async (productId: number) => {
    try {
      await productService.deleteTrackedProduct(productId);
      setTrackedProducts(trackedProducts.filter(product => product.id !== productId));
    } catch (err: any) {
      console.error('Error deleting tracked product:', err);
      alert(err.response?.data?.detail || 'Ошибка при удалении товара из отслеживаемых');
    }
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        <BarChartIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
        Отслеживаемые товары
      </Typography>

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : trackedProducts.length === 0 ? (
        <Card variant="outlined" sx={{ mb: 4 }}>
          <CardContent>
            <Typography variant="h6" align="center" sx={{ my: 2 }}>
              У вас пока нет отслеживаемых товаров
            </Typography>
            <Typography variant="body1" align="center">
              Добавьте товары в отслеживание на странице анализа товара
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <TableContainer component={Paper}>
          <Table sx={{ minWidth: 650 }} aria-label="tracked products table">
            <TableHead>
              <TableRow>
                <TableCell>Артикул</TableCell>
                <TableCell>Наименование</TableCell>
                <TableCell align="right">Цена (руб.)</TableCell>
                <TableCell>Последняя проверка</TableCell>
                <TableCell align="center">Действия</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {trackedProducts.map((product) => (
                <TableRow key={product.id}>
                  <TableCell component="th" scope="row">
                    {product.article}
                  </TableCell>
                  <TableCell>{product.name || 'Нет данных'}</TableCell>
                  <TableCell align="right">{product.price ? product.price.toLocaleString() : 'Нет данных'}</TableCell>
                  <TableCell>{product.last_checked || 'Не проверялся'}</TableCell>
                  <TableCell align="center">
                    <IconButton
                      aria-label="delete"
                      color="error"
                      onClick={() => handleDeleteTrackedProduct(product.id)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default Tracking; 