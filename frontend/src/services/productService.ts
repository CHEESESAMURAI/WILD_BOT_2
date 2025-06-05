import api from './api';

export interface Product {
  id: number;
  article: string;
  name: string;
  price: number;
  user_id: number;
  last_checked: string;
}

export interface ProductAnalysisResult {
  article: string;
  name: string;
  brand?: string;
  price: number;
  rating?: number;
  reviews_count?: number;
  sales_data?: any;
  position_data?: any;
  charts?: string[];
  recommendations?: string[];
}

export interface TrackProductData {
  article: string;
  name?: string;
  price?: number;
  user_id: number;
}

// Тестовая реализация - возвращает моковые данные
const analyzeProduct = async (article: string): Promise<ProductAnalysisResult> => {
  // В реальном приложении здесь был бы запрос к API
  return {
    article,
    name: `Товар ${article}`,
    brand: 'Тестовый бренд',
    price: 1999,
    rating: 4.7,
    reviews_count: 120,
    recommendations: [
      'Рекомендация 1 для товара',
      'Рекомендация 2 для товара',
      'Рекомендация 3 для товара'
    ]
  };
};

const trackProduct = async (data: TrackProductData): Promise<Product> => {
  // В реальном приложении здесь был бы запрос к API
  return {
    id: Math.floor(Math.random() * 1000),
    article: data.article,
    name: data.name || `Товар ${data.article}`,
    price: data.price || 0,
    user_id: data.user_id,
    last_checked: new Date().toISOString()
  };
};

const getTrackedProducts = async (userId: number): Promise<Product[]> => {
  // В реальном приложении здесь был бы запрос к API
  return [
    {
      id: 1,
      article: '12345678',
      name: 'Тестовый товар 1',
      price: 1999,
      user_id: userId,
      last_checked: new Date().toISOString()
    },
    {
      id: 2,
      article: '87654321',
      name: 'Тестовый товар 2',
      price: 2999,
      user_id: userId,
      last_checked: new Date().toISOString()
    }
  ];
};

const deleteTrackedProduct = async (productId: number): Promise<Product> => {
  // В реальном приложении здесь был бы запрос к API
  return {
    id: productId,
    article: '12345678',
    name: 'Удаленный товар',
    price: 1999,
    user_id: 1,
    last_checked: new Date().toISOString()
  };
};

const productService = {
  analyzeProduct,
  trackProduct,
  getTrackedProducts,
  deleteTrackedProduct,
};

export default productService; 