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
  List,
  ListItem,
  ListItemText,
  Alert,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import CategoryIcon from '@mui/icons-material/Category';
import nicheService, { NicheAnalysisResult } from '../services/nicheService';

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

export const NicheAnalysis: React.FC = () => {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<NicheAnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    
    if (!query) {
      setError('Пожалуйста, введите поисковый запрос');
      return;
    }
    
    try {
      setIsLoading(true);
      const data = await nicheService.analyzeNiche(query);
      setResult(data);
    } catch (err: any) {
      console.error('Error analyzing niche:', err);
      setError(err.response?.data?.detail || 'Ошибка при анализе ниши');
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
        <Box>
          <Card sx={{ mb: 4 }}>
            <CardContent>
              <Typography variant="h5" component="div" gutterBottom>
                Результаты анализа ниши: {result.niche_name}
              </Typography>
              
              <Grid container spacing={3} sx={{ mt: 1 }}>
                <Grid item xs={12} sm={4}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Всего товаров
                      </Typography>
                      <Typography variant="h4" component="div">
                        {result.total_products.toLocaleString()}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                
                <Grid item xs={12} sm={4}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Средняя цена
                      </Typography>
                      <Typography variant="h4" component="div">
                        {result.avg_price.toLocaleString()} ₽
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                
                <Grid item xs={12} sm={4}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Диапазон цен
                      </Typography>
                      <Typography variant="h6" component="div">
                        {result.price_range.min.toLocaleString()} - {result.price_range.max.toLocaleString()} ₽
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
          
          <Box sx={{ width: '100%' }}>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs value={tabValue} onChange={handleTabChange} aria-label="basic tabs example">
                <Tab label="Бренды" />
                <Tab label="Рекомендации" />
                <Tab label="Графики" />
              </Tabs>
            </Box>
            
            <TabPanel value={tabValue} index={0}>
              <Typography variant="h6" gutterBottom>
                Топ брендов в нише:
              </Typography>
              <TableContainer component={Paper}>
                <Table sx={{ minWidth: 650 }} aria-label="simple table">
                  <TableHead>
                    <TableRow>
                      <TableCell>Бренд</TableCell>
                      <TableCell align="right">Количество товаров</TableCell>
                      <TableCell align="right">Доля рынка</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {result.top_brands.map((brand) => (
                      <TableRow key={brand.name}>
                        <TableCell component="th" scope="row">
                          {brand.name}
                        </TableCell>
                        <TableCell align="right">{brand.count}</TableCell>
                        <TableCell align="right">
                          {((brand.count / result.total_products) * 100).toFixed(2)}%
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </TabPanel>
            
            <TabPanel value={tabValue} index={1}>
              <Typography variant="h6" gutterBottom>
                Рекомендации по нише:
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
                <Typography>Нет рекомендаций для данной ниши</Typography>
              )}
            </TabPanel>
            
            <TabPanel value={tabValue} index={2}>
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
                <Typography>Нет графиков для данной ниши</Typography>
              )}
            </TabPanel>
          </Box>
        </Box>
      )}
    </Box>
  );
}; 