import React, { useState } from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  Grid,
  TextField,
  Button,
  CircularProgress,
  Tabs,
  Tab,
  Slider,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  FormHelperText
} from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import SearchIcon from '@mui/icons-material/Search';
import StorefrontIcon from '@mui/icons-material/Storefront';
import CategoryIcon from '@mui/icons-material/Category';
import LocalOfferIcon from '@mui/icons-material/LocalOffer';
import BusinessIcon from '@mui/icons-material/Business';
import ListIcon from '@mui/icons-material/List';

interface TabPanelProps {
  children?: React.ReactNode;
  index: any;
  value: any;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

interface OracleQueryResult {
  query: string;
  rating: number;
  frequency30d: number;
  dynamicsChange30d: number;
  dynamicsChange60d: number;
  dynamicsChange90d: number;
  revenue30dFirstPages: number;
  avgRevenue30dFirstPages: number;
  lostRevenuePercent30d: number;
  monopolyPercent: number;
  avgPriceFirstPages: number;
  adsPercentFirstPage: number;
}

interface OracleDetailedResult {
  name: string;
  articleId: string;
  brand: string;
  supplier: string;
  revenue: number;
  lostRevenue: number;
  orders: number;
}

const QueryOraclePage: React.FC = () => {
  // States for form inputs
  const [queriesCount, setQueriesCount] = useState<number>(3);
  const [month, setMonth] = useState<string>('current');
  const [revenue30d, setRevenue30d] = useState<string>('');
  const [frequency30d, setFrequency30d] = useState<string>('');
  const [filterType, setFilterType] = useState<number>(0); // 0: По товарам, 1: По брендам, etc.
  
  // Loading state
  const [isLoading, setIsLoading] = useState<boolean>(false);
  
  // Result data
  const [queryResults, setQueryResults] = useState<OracleQueryResult[]>([]);
  const [detailedResults, setDetailedResults] = useState<OracleDetailedResult[]>([]);

  // Handle form submission
  const handleSubmit = () => {
    setIsLoading(true);
    
    // Generate mock data based on inputs
    setTimeout(() => {
      // Generate mock query results
      if (filterType !== 4) { // Not "По запросам"
        const mockQueryResults = generateMockQueryResults(queriesCount);
        setQueryResults(mockQueryResults);
        setDetailedResults([]);
      } else {
        // For "По запросам" filter type
        const mockDetailedResults = generateMockDetailedResults(queriesCount);
        setDetailedResults(mockDetailedResults);
        setQueryResults([]);
      }
      
      setIsLoading(false);
    }, 1500);
  };

  // Generate mock data for the table
  const generateMockQueryResults = (count: number): OracleQueryResult[] => {
    const queries = [
      'платье женское', 'футболка мужская', 'джинсы', 'кроссовки', 
      'куртка', 'пальто', 'юбка', 'шорты', 'свитер', 'рубашка'
    ];
    
    return Array.from({ length: count }, (_, idx) => ({
      query: queries[idx % queries.length],
      rating: Math.floor(Math.random() * 100) + 1,
      frequency30d: Math.floor(Math.random() * 10000) + 100,
      dynamicsChange30d: (Math.random() * 60) - 20, // -20 to +40
      dynamicsChange60d: (Math.random() * 80) - 30, // -30 to +50
      dynamicsChange90d: (Math.random() * 100) - 40, // -40 to +60
      revenue30dFirstPages: Math.floor(Math.random() * 10000000) + 100000,
      avgRevenue30dFirstPages: Math.floor(Math.random() * 1000000) + 10000,
      lostRevenuePercent30d: Math.floor(Math.random() * 90) + 10,
      monopolyPercent: Math.floor(Math.random() * 100),
      avgPriceFirstPages: Math.floor(Math.random() * 5000) + 500,
      adsPercentFirstPage: Math.floor(Math.random() * 100)
    }));
  };

  // Generate mock detailed results
  const generateMockDetailedResults = (count: number): OracleDetailedResult[] => {
    const products = [
      'Платье летнее', 'Футболка хлопковая', 'Джинсы прямые', 'Кроссовки беговые', 
      'Куртка демисезонная', 'Пальто шерстяное', 'Юбка миди', 'Шорты джинсовые', 
      'Свитер вязаный', 'Рубашка офисная'
    ];
    
    const brands = ['WildFashion', 'UrbanStyle', 'CityLook', 'SportMax', 'FashionPro'];
    const suppliers = ['ТексПром', 'МодныйДом', 'ФабрикаСтиля', 'ОдеждаПлюс', 'МегаТекстиль'];
    
    return Array.from({ length: count * 2 }, (_, idx) => ({
      name: products[idx % products.length],
      articleId: `${Math.floor(10000000 + Math.random() * 90000000)}`,
      brand: brands[idx % brands.length],
      supplier: suppliers[idx % suppliers.length],
      revenue: Math.floor(Math.random() * 1000000) + 10000,
      lostRevenue: Math.floor(Math.random() * 500000) + 5000,
      orders: Math.floor(Math.random() * 1000) + 10
    }));
  };

  // Format currency
  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0
    }).format(value);
  };

  // Format percentage
  const formatPercent = (value: number): string => {
    return `${value.toFixed(1)}%`;
  };

  // Format number with thousands separator
  const formatNumber = (value: number): string => {
    return new Intl.NumberFormat('ru-RU').format(value);
  };

  const handleFilterTypeChange = (event: React.SyntheticEvent, newValue: number) => {
    setFilterType(newValue);
    // Reset results when changing filter type
    setQueryResults([]);
    setDetailedResults([]);
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Оракул запросов
        </Typography>
        
        <Typography variant="body1" paragraph color="text.secondary" sx={{ mb: 4 }}>
          Анализ и прогнозирование эффективности поисковых запросов на Wildberries
        </Typography>
        
        <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
          <Box sx={{ maxWidth: 800, mx: 'auto' }}>
            <Typography variant="h5" gutterBottom>
              Параметры анализа
            </Typography>
            
            <Grid container spacing={3} sx={{ mt: 2 }}>
              <Grid item xs={12} sm={6}>
                <Typography id="queries-count-slider" gutterBottom>
                  Количество запросов: {queriesCount}
                </Typography>
                <Slider
                  value={queriesCount}
                  onChange={(_, value) => setQueriesCount(value as number)}
                  step={1}
                  marks
                  min={1}
                  max={5}
                  aria-labelledby="queries-count-slider"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel id="month-select-label">Месяц</InputLabel>
                  <Select
                    labelId="month-select-label"
                    value={month}
                    label="Месяц"
                    onChange={(e) => setMonth(e.target.value)}
                  >
                    <MenuItem value="current">Текущий месяц</MenuItem>
                    <MenuItem value="previous">Предыдущий месяц</MenuItem>
                    <MenuItem value="twoMonthsAgo">Два месяца назад</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Выручка за 30 дней (₽)"
                  variant="outlined"
                  value={revenue30d}
                  onChange={(e) => setRevenue30d(e.target.value)}
                  placeholder="Например: 500000"
                  type="number"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Частотность за 30 дней"
                  variant="outlined"
                  value={frequency30d}
                  onChange={(e) => setFrequency30d(e.target.value)}
                  placeholder="Например: 5000"
                  type="number"
                />
              </Grid>
              
              <Grid item xs={12}>
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                  <Button 
                    variant="contained" 
                    size="large" 
                    onClick={handleSubmit}
                    disabled={isLoading}
                    startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <SearchIcon />}
                  >
                    {isLoading ? 'Обработка...' : 'Проанализировать'}
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </Box>
        </Paper>
        
        {(queryResults.length > 0 || detailedResults.length > 0) && (
          <Paper elevation={3} sx={{ p: 3 }}>
            <Tabs 
              value={filterType} 
              onChange={handleFilterTypeChange}
              variant="scrollable"
              scrollButtons="auto"
              sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}
            >
              <Tab icon={<StorefrontIcon />} label="По товарам" />
              <Tab icon={<LocalOfferIcon />} label="По брендам" />
              <Tab icon={<BusinessIcon />} label="По поставщикам" />
              <Tab icon={<CategoryIcon />} label="По категориям" />
              <Tab icon={<ListIcon />} label="По запросам" />
            </Tabs>
            
            <TabPanel value={filterType} index={0}>
              <Box sx={{ mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Анализ по товарам
                </Typography>
                <FormHelperText>
                  Результаты анализа запросов с фокусом на товары
                </FormHelperText>
              </Box>
              <TableContainer>
                <Table sx={{ minWidth: 650 }} size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Запрос</TableCell>
                      <TableCell>Рейтинг</TableCell>
                      <TableCell>Част. за 30д</TableCell>
                      <TableCell>Дин. 30д</TableCell>
                      <TableCell>Дин. 60д</TableCell>
                      <TableCell>Дин. 90д</TableCell>
                      <TableCell>Выручка (₽)</TableCell>
                      <TableCell>Ср. выручка (₽)</TableCell>
                      <TableCell>% упущ. выручки</TableCell>
                      <TableCell>% монопольности</TableCell>
                      <TableCell>Ср. цена (₽)</TableCell>
                      <TableCell>% в рекламе</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {queryResults.map((row, index) => (
                      <TableRow key={index} hover>
                        <TableCell><strong>{row.query}</strong></TableCell>
                        <TableCell>{row.rating}</TableCell>
                        <TableCell>{formatNumber(row.frequency30d)}</TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            {row.dynamicsChange30d > 0 ? 
                              <TrendingUpIcon fontSize="small" color="success" /> : 
                              <TrendingDownIcon fontSize="small" color="error" />}
                            <Typography 
                              variant="body2" 
                              color={row.dynamicsChange30d > 0 ? 'success.main' : 'error.main'}
                            >
                              {formatPercent(row.dynamicsChange30d)}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            {row.dynamicsChange60d > 0 ? 
                              <TrendingUpIcon fontSize="small" color="success" /> : 
                              <TrendingDownIcon fontSize="small" color="error" />}
                            <Typography 
                              variant="body2"
                              color={row.dynamicsChange60d > 0 ? 'success.main' : 'error.main'}
                            >
                              {formatPercent(row.dynamicsChange60d)}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            {row.dynamicsChange90d > 0 ? 
                              <TrendingUpIcon fontSize="small" color="success" /> : 
                              <TrendingDownIcon fontSize="small" color="error" />}
                            <Typography 
                              variant="body2"
                              color={row.dynamicsChange90d > 0 ? 'success.main' : 'error.main'}
                            >
                              {formatPercent(row.dynamicsChange90d)}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>{formatCurrency(row.revenue30dFirstPages)}</TableCell>
                        <TableCell>{formatCurrency(row.avgRevenue30dFirstPages)}</TableCell>
                        <TableCell>{formatPercent(row.lostRevenuePercent30d)}</TableCell>
                        <TableCell>{formatPercent(row.monopolyPercent)}</TableCell>
                        <TableCell>{formatCurrency(row.avgPriceFirstPages)}</TableCell>
                        <TableCell>{formatPercent(row.adsPercentFirstPage)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </TabPanel>
            
            <TabPanel value={filterType} index={1}>
              <Box sx={{ mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Анализ по брендам
                </Typography>
                <FormHelperText>
                  Результаты анализа запросов с фокусом на бренды
                </FormHelperText>
              </Box>
              <TableContainer>
                <Table sx={{ minWidth: 650 }} size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Запрос</TableCell>
                      <TableCell>Рейтинг</TableCell>
                      <TableCell>Част. за 30д</TableCell>
                      <TableCell>Дин. 30д</TableCell>
                      <TableCell>Дин. 60д</TableCell>
                      <TableCell>Дин. 90д</TableCell>
                      <TableCell>Выручка (₽)</TableCell>
                      <TableCell>Ср. выручка (₽)</TableCell>
                      <TableCell>% упущ. выручки</TableCell>
                      <TableCell>% монопольности</TableCell>
                      <TableCell>Ср. цена (₽)</TableCell>
                      <TableCell>% в рекламе</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {queryResults.map((row, index) => (
                      <TableRow key={index} hover>
                        <TableCell><strong>{row.query}</strong></TableCell>
                        <TableCell>{row.rating}</TableCell>
                        <TableCell>{formatNumber(row.frequency30d)}</TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            {row.dynamicsChange30d > 0 ? 
                              <TrendingUpIcon fontSize="small" color="success" /> : 
                              <TrendingDownIcon fontSize="small" color="error" />}
                            <Typography 
                              variant="body2" 
                              color={row.dynamicsChange30d > 0 ? 'success.main' : 'error.main'}
                            >
                              {formatPercent(row.dynamicsChange30d)}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            {row.dynamicsChange60d > 0 ? 
                              <TrendingUpIcon fontSize="small" color="success" /> : 
                              <TrendingDownIcon fontSize="small" color="error" />}
                            <Typography 
                              variant="body2"
                              color={row.dynamicsChange60d > 0 ? 'success.main' : 'error.main'}
                            >
                              {formatPercent(row.dynamicsChange60d)}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            {row.dynamicsChange90d > 0 ? 
                              <TrendingUpIcon fontSize="small" color="success" /> : 
                              <TrendingDownIcon fontSize="small" color="error" />}
                            <Typography 
                              variant="body2"
                              color={row.dynamicsChange90d > 0 ? 'success.main' : 'error.main'}
                            >
                              {formatPercent(row.dynamicsChange90d)}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>{formatCurrency(row.revenue30dFirstPages)}</TableCell>
                        <TableCell>{formatCurrency(row.avgRevenue30dFirstPages)}</TableCell>
                        <TableCell>{formatPercent(row.lostRevenuePercent30d)}</TableCell>
                        <TableCell>{formatPercent(row.monopolyPercent)}</TableCell>
                        <TableCell>{formatCurrency(row.avgPriceFirstPages)}</TableCell>
                        <TableCell>{formatPercent(row.adsPercentFirstPage)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </TabPanel>
            
            <TabPanel value={filterType} index={2}>
              <Box sx={{ mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Анализ по поставщикам
                </Typography>
                <FormHelperText>
                  Результаты анализа запросов с фокусом на поставщиков
                </FormHelperText>
              </Box>
              <TableContainer>
                <Table sx={{ minWidth: 650 }} size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Запрос</TableCell>
                      <TableCell>Рейтинг</TableCell>
                      <TableCell>Част. за 30д</TableCell>
                      <TableCell>Дин. 30д</TableCell>
                      <TableCell>Дин. 60д</TableCell>
                      <TableCell>Дин. 90д</TableCell>
                      <TableCell>Выручка (₽)</TableCell>
                      <TableCell>Ср. выручка (₽)</TableCell>
                      <TableCell>% упущ. выручки</TableCell>
                      <TableCell>% монопольности</TableCell>
                      <TableCell>Ср. цена (₽)</TableCell>
                      <TableCell>% в рекламе</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {queryResults.map((row, index) => (
                      <TableRow key={index} hover>
                        <TableCell><strong>{row.query}</strong></TableCell>
                        <TableCell>{row.rating}</TableCell>
                        <TableCell>{formatNumber(row.frequency30d)}</TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            {row.dynamicsChange30d > 0 ? 
                              <TrendingUpIcon fontSize="small" color="success" /> : 
                              <TrendingDownIcon fontSize="small" color="error" />}
                            <Typography 
                              variant="body2" 
                              color={row.dynamicsChange30d > 0 ? 'success.main' : 'error.main'}
                            >
                              {formatPercent(row.dynamicsChange30d)}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            {row.dynamicsChange60d > 0 ? 
                              <TrendingUpIcon fontSize="small" color="success" /> : 
                              <TrendingDownIcon fontSize="small" color="error" />}
                            <Typography 
                              variant="body2"
                              color={row.dynamicsChange60d > 0 ? 'success.main' : 'error.main'}
                            >
                              {formatPercent(row.dynamicsChange60d)}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            {row.dynamicsChange90d > 0 ? 
                              <TrendingUpIcon fontSize="small" color="success" /> : 
                              <TrendingDownIcon fontSize="small" color="error" />}
                            <Typography 
                              variant="body2"
                              color={row.dynamicsChange90d > 0 ? 'success.main' : 'error.main'}
                            >
                              {formatPercent(row.dynamicsChange90d)}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>{formatCurrency(row.revenue30dFirstPages)}</TableCell>
                        <TableCell>{formatCurrency(row.avgRevenue30dFirstPages)}</TableCell>
                        <TableCell>{formatPercent(row.lostRevenuePercent30d)}</TableCell>
                        <TableCell>{formatPercent(row.monopolyPercent)}</TableCell>
                        <TableCell>{formatCurrency(row.avgPriceFirstPages)}</TableCell>
                        <TableCell>{formatPercent(row.adsPercentFirstPage)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </TabPanel>
            
            <TabPanel value={filterType} index={3}>
              <Box sx={{ mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Анализ по категориям
                </Typography>
                <FormHelperText>
                  Результаты анализа запросов с фокусом на категории товаров
                </FormHelperText>
              </Box>
              <TableContainer>
                <Table sx={{ minWidth: 650 }} size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Запрос</TableCell>
                      <TableCell>Рейтинг</TableCell>
                      <TableCell>Част. за 30д</TableCell>
                      <TableCell>Дин. 30д</TableCell>
                      <TableCell>Дин. 60д</TableCell>
                      <TableCell>Дин. 90д</TableCell>
                      <TableCell>Выручка (₽)</TableCell>
                      <TableCell>Ср. выручка (₽)</TableCell>
                      <TableCell>% упущ. выручки</TableCell>
                      <TableCell>% монопольности</TableCell>
                      <TableCell>Ср. цена (₽)</TableCell>
                      <TableCell>% в рекламе</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {queryResults.map((row, index) => (
                      <TableRow key={index} hover>
                        <TableCell><strong>{row.query}</strong></TableCell>
                        <TableCell>{row.rating}</TableCell>
                        <TableCell>{formatNumber(row.frequency30d)}</TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            {row.dynamicsChange30d > 0 ? 
                              <TrendingUpIcon fontSize="small" color="success" /> : 
                              <TrendingDownIcon fontSize="small" color="error" />}
                            <Typography 
                              variant="body2" 
                              color={row.dynamicsChange30d > 0 ? 'success.main' : 'error.main'}
                            >
                              {formatPercent(row.dynamicsChange30d)}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            {row.dynamicsChange60d > 0 ? 
                              <TrendingUpIcon fontSize="small" color="success" /> : 
                              <TrendingDownIcon fontSize="small" color="error" />}
                            <Typography 
                              variant="body2"
                              color={row.dynamicsChange60d > 0 ? 'success.main' : 'error.main'}
                            >
                              {formatPercent(row.dynamicsChange60d)}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            {row.dynamicsChange90d > 0 ? 
                              <TrendingUpIcon fontSize="small" color="success" /> : 
                              <TrendingDownIcon fontSize="small" color="error" />}
                            <Typography 
                              variant="body2"
                              color={row.dynamicsChange90d > 0 ? 'success.main' : 'error.main'}
                            >
                              {formatPercent(row.dynamicsChange90d)}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>{formatCurrency(row.revenue30dFirstPages)}</TableCell>
                        <TableCell>{formatCurrency(row.avgRevenue30dFirstPages)}</TableCell>
                        <TableCell>{formatPercent(row.lostRevenuePercent30d)}</TableCell>
                        <TableCell>{formatPercent(row.monopolyPercent)}</TableCell>
                        <TableCell>{formatCurrency(row.avgPriceFirstPages)}</TableCell>
                        <TableCell>{formatPercent(row.adsPercentFirstPage)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </TabPanel>
            
            <TabPanel value={filterType} index={4}>
              <Box sx={{ mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Анализ по запросам
                </Typography>
                <FormHelperText>
                  Детальный анализ товаров по запросам
                </FormHelperText>
              </Box>
              <TableContainer>
                <Table sx={{ minWidth: 650 }} size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Название</TableCell>
                      <TableCell>Артикул</TableCell>
                      <TableCell>Бренд</TableCell>
                      <TableCell>Поставщик</TableCell>
                      <TableCell>Выручка (₽)</TableCell>
                      <TableCell>Упущенная выручка (₽)</TableCell>
                      <TableCell>Заказов</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {detailedResults.map((row, index) => (
                      <TableRow key={index} hover>
                        <TableCell><strong>{row.name}</strong></TableCell>
                        <TableCell>
                          <Chip 
                            label={row.articleId} 
                            size="small" 
                            color="primary" 
                            variant="outlined" 
                          />
                        </TableCell>
                        <TableCell>{row.brand}</TableCell>
                        <TableCell>{row.supplier}</TableCell>
                        <TableCell>{formatCurrency(row.revenue)}</TableCell>
                        <TableCell>{formatCurrency(row.lostRevenue)}</TableCell>
                        <TableCell>{formatNumber(row.orders)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </TabPanel>
          </Paper>
        )}
      </Box>
    </Container>
  );
};

export default QueryOraclePage; 