import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from typing import List, Dict
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class NicheVisualizer:
    """Class for visualizing niche analysis data"""
    
    def __init__(self):
        # Use a built-in style instead of 'seaborn'
        plt.style.use('seaborn-v0_8')  # or 'seaborn-darkgrid' for older versions
        sns.set_theme()  # This will set the seaborn theme properly
    
    def create_price_distribution(self, products: List[Dict], save_path: str = None) -> None:
        """Create price distribution visualization"""
        df = pd.DataFrame(products)
        
        plt.figure(figsize=(10, 6))
        sns.histplot(data=df, x='price', bins=30)
        plt.title('Price Distribution in Category')
        plt.xlabel('Price (₽)')
        plt.ylabel('Count')
        
        if save_path:
            plt.savefig(save_path)
        else:
            plt.show()
    
    def create_sales_volume_plot(self, products: List[Dict], save_path: str = None) -> None:
        """Create sales volume visualization"""
        df = pd.DataFrame(products)
        
        plt.figure(figsize=(12, 6))
        sns.scatterplot(data=df, x='price', y='sales_volume', size='rating', alpha=0.6)
        plt.title('Sales Volume vs Price (bubble size = rating)')
        plt.xlabel('Price (₽)')
        plt.ylabel('Sales Volume')
        
        if save_path:
            plt.savefig(save_path)
        else:
            plt.show()
    
    def create_brand_analysis(self, products: List[Dict], save_path: str = None) -> None:
        """Create brand analysis visualization"""
        df = pd.DataFrame(products)
        brand_stats = df.groupby('brand').agg({
            'sales_volume': 'sum',
            'rating': 'mean',
            'reviews_count': 'sum'
        }).sort_values('sales_volume', ascending=False).head(10)
        
        fig, ax1 = plt.subplots(figsize=(12, 6))
        ax2 = ax1.twinx()
        
        x = range(len(brand_stats))
        width = 0.35
        
        ax1.bar(x, brand_stats['sales_volume'], width, label='Sales Volume')
        ax2.plot(x, brand_stats['rating'], 'r-', label='Average Rating')
        
        plt.title('Top 10 Brands Analysis')
        ax1.set_xlabel('Brands')
        ax1.set_ylabel('Sales Volume')
        ax2.set_ylabel('Average Rating')
        
        plt.xticks(x, brand_stats.index, rotation=45, ha='right')
        
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2)
        
        if save_path:
            plt.savefig(save_path)
        else:
            plt.show()
    
    def create_interactive_dashboard(self, products: List[Dict], historical_data: List[Dict]) -> None:
        """Create interactive dashboard using Plotly"""
        df = pd.DataFrame(products)
        hist_df = pd.DataFrame([d['data'] for d in historical_data])
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Price Distribution', 'Sales vs Price', 
                          'Brand Performance', 'Historical Trends')
        )
        
        # Price Distribution
        fig.add_trace(
            go.Histogram(x=df['price'], name='Price Distribution'),
            row=1, col=1
        )
        
        # Sales vs Price
        fig.add_trace(
            go.Scatter(x=df['price'], y=df['sales_volume'],
                      mode='markers', name='Sales vs Price',
                      marker=dict(size=df['rating']*2)),
            row=1, col=2
        )
        
        # Brand Performance
        brand_stats = df.groupby('brand').agg({
            'sales_volume': 'sum',
            'rating': 'mean'
        }).sort_values('sales_volume', ascending=False).head(10)
        
        fig.add_trace(
            go.Bar(x=brand_stats.index, y=brand_stats['sales_volume'],
                  name='Brand Sales'),
            row=2, col=1
        )
        
        # Historical Trends
        fig.add_trace(
            go.Scatter(x=hist_df['timestamp'], y=hist_df['avg_price'],
                      mode='lines', name='Average Price'),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            height=800,
            showlegend=True,
            title_text="Niche Analysis Dashboard"
        )
        
        # Show the dashboard
        fig.show()
    
    def generate_report(self, products: List[Dict], analysis: Dict, 
                       opportunities: List[Dict], save_path: str = None) -> str:
        """Generate a comprehensive report"""
        report = []
        
        # Header
        report.append("# Niche Analysis Report")
        report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Summary
        report.append("## Summary")
        report.append(f"- Total Products: {analysis['total_products']}")
        report.append(f"- Average Price: {analysis['avg_price']:.2f} ₽")
        report.append(f"- Price Range: {analysis['price_range']['min']:.2f} - {analysis['price_range']['max']:.2f} ₽")
        report.append(f"- Average Rating: {analysis['avg_rating']:.2f}")
        report.append(f"- Average Reviews: {analysis['avg_reviews']:.2f}\n")
        
        # Top Brands
        report.append("## Top Brands")
        for brand, sales in analysis['top_brands'].items():
            report.append(f"- {brand}: {sales} sales")
        
        # Top Suppliers
        report.append("\n## Top Suppliers")
        for supplier, sales in analysis['top_suppliers'].items():
            report.append(f"- {supplier}: {sales} sales")
        
        # Sales Distribution
        report.append("\n## Sales Distribution")
        for level, count in analysis['sales_distribution'].items():
            report.append(f"- {level.title()}: {count} products")
        
        # Opportunities
        report.append("\n## Market Opportunities")
        for opp in opportunities:
            report.append(f"- **{opp['type']}** (Confidence: {opp['confidence']:.2f})")
            report.append(f"  {opp['description']}")
        
        report_text = "\n".join(report)
        
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
        
        return report_text 