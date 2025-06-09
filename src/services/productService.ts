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

const analyzeProduct = async (article: string): Promise<ProductAnalysisResult> => {
  const response = await api.get<ProductAnalysisResult>(`/products/analyze/${article}`);
  return response.data;
};

const trackProduct = async (data: TrackProductData): Promise<Product> => {
  const response = await api.post<Product>('/products/track', data);
  return response.data;
};

const getTrackedProducts = async (userId: number): Promise<Product[]> => {
  const response = await api.get<Product[]>(`/products/track/user/${userId}`);
  return response.data;
};

const deleteTrackedProduct = async (productId: number): Promise<Product> => {
  const response = await api.delete<Product>(`/products/track/${productId}`);
  return response.data;
};

const productService = {
  analyzeProduct,
  trackProduct,
  getTrackedProducts,
  deleteTrackedProduct,
};

export default productService; 