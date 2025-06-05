import React from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Container,
} from '@mui/material';
import ConstructionIcon from '@mui/icons-material/Construction';

interface ComingSoonPageProps {
  title?: string;
}

const ComingSoonPage: React.FC<ComingSoonPageProps> = ({ title }) => {
  // Простая функция для возврата на дашборд
  const goToDashboard = () => {
    window.location.href = '/dashboard';
  };
  
  const featureTitle = title || 'Эта функция';
  
  return (
    <Container maxWidth="md">
      <Paper elevation={3} sx={{ p: 4, mt: 5, textAlign: 'center' }}>
        <ConstructionIcon sx={{ fontSize: 80, color: 'warning.main', mb: 2 }} />
        
        <Typography variant="h4" gutterBottom>
          {featureTitle} в разработке
        </Typography>
        
        <Typography variant="body1" color="text.secondary" paragraph sx={{ mb: 4 }}>
          Мы активно работаем над этой функцией и скоро она будет доступна.
          Следите за обновлениями системы.
        </Typography>
        
        <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
          <Button 
            variant="contained" 
            onClick={goToDashboard}
          >
            Вернуться в личный кабинет
          </Button>
        </Box>
      </Paper>
    </Container>
  );
};

export default ComingSoonPage; 