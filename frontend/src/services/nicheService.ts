import api from './api';

export interface PriceRange {
  min: number;
  max: number;
}

export interface TopBrand {
  name: string;
  count: number;
}

export interface NicheAnalysisResult {
  niche_name: string;
  total_products: number;
  avg_price: number;
  price_range: PriceRange;
  top_brands: TopBrand[];
  sales_trend?: any;
  charts?: string[];
  recommendations?: string[];
}

const analyzeNiche = async (query: string): Promise<NicheAnalysisResult> => {
  const response = await api.get<NicheAnalysisResult>('/niches/analyze', {
    params: { query }
  });
  return response.data;
};

const nicheService = {
  analyzeNiche
};

export default nicheService; 