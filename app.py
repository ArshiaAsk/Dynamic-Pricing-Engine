import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime
import math

# Page configuration
st.set_page_config(
    page_title="Dynamic Pricing Engine",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
    <style>
    .main {
        padding: 1rem;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# Title and description
st.title("💰 Dynamic Pricing Engine")
st.markdown("""
    **AI-Powered Price Optimization System**
    
    Optimize product prices using machine learning demand forecasting and business constraints.
""")

# Sidebar for API configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    api_url = st.text_input(
        "API URL",
        value="http://localhost:8000",
        help="Enter the FastAPI server URL"
    )
    endpoint = f"{api_url}/v1/optimize-price"

# Create tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Quick Pricing",
    "🔧 Advanced Settings",
    "📈 Batch Pricing",
    "📚 About"
])

# ============= TAB 1: QUICK PRICING =============
with tab1:
    st.header("Quick Pricing Optimization")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📦 Product Information")
        product_id = st.number_input("Product ID", value=1, min_value=0, step=1)
        competitor_price = st.number_input(
            "Competitor Price ($)",
            value=89.99,
            min_value=0.01,
            format="%.2f"
        )
    
    with col2:
        st.subheader("📅 Date & Time Information")
        selected_date = st.date_input("Date", datetime.now())
        
        # Calculate date features
        dow = selected_date.weekday()
        is_weekend = 1 if dow >= 5 else 0
        week = selected_date.isocalendar()[1]
        month = selected_date.month
        
        # Calculate annual seasonality
        day_of_year = selected_date.timetuple().tm_yday
        sin_annual = math.sin(2 * math.pi * day_of_year / 365)
        cos_annual = math.cos(2 * math.pi * day_of_year / 365)
        
        st.info(f"""
        📍 Date Features:
        - Day of Week: {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][dow]} ({dow})
        - Is Weekend: {bool(is_weekend)}
        - Week: {week}
        - Month: {month}
        """)
    
    # Historical sales data
    st.subheader("📊 Historical Sales Data (Units Sold)")
    hist_col1, hist_col2, hist_col3 = st.columns(3)
    
    with hist_col1:
        lag_1 = st.number_input("Last Day (Lag-1)", value=45.0, min_value=0.0, format="%.1f")
        lag_7 = st.number_input("Last Week (Lag-7)", value=42.0, min_value=0.0, format="%.1f")
        lag_14 = st.number_input("2 Weeks Ago (Lag-14)", value=40.0, min_value=0.0, format="%.1f")
    
    with hist_col2:
        roll_mean_7 = st.number_input("7-Day Average", value=43.5, min_value=0.0, format="%.1f")
        roll_mean_14 = st.number_input("14-Day Average", value=41.2, min_value=0.0, format="%.1f")
        roll_mean_28 = st.number_input("28-Day Average", value=39.8, min_value=0.0, format="%.1f")
    
    with hist_col3:
        roll_std_7 = st.number_input("7-Day Std Dev", value=5.2, min_value=0.0, format="%.1f")
        roll_std_14 = st.number_input("14-Day Std Dev", value=6.1, min_value=0.0, format="%.1f")
        roll_std_28 = st.number_input("28-Day Std Dev", value=7.3, min_value=0.0, format="%.1f")
    
    # Pricing constraints
    st.subheader("💵 Pricing & Business Constraints")
    constraint_col1, constraint_col2 = st.columns(2)
    
    with constraint_col1:
        price_min = st.number_input("Minimum Price ($)", value=70.0, min_value=0.01, format="%.2f")
        price_max = st.number_input("Maximum Price ($)", value=110.0, min_value=0.01, format="%.2f")
    
    with constraint_col2:
        cost = st.number_input("Product Cost ($)", value=60.0, min_value=0.0, format="%.2f")
        min_margin_pct = st.slider("Min Profit Margin (%)", 5, 50, 15) / 100.0
    
    optimization_method = st.selectbox(
        "Optimization Method",
        ["bayesian", "grid_search"],
        help="bayesian: Fast Bayesian optimization | grid_search: Exhaustive search"
    )
    
    inventory_limit = st.number_input(
        "Inventory Limit (units, optional)",
        value=0,
        min_value=0,
        step=1,
        help="Leave 0 to ignore inventory constraint"
    )
    
    # Submit button
    if st.button("🚀 Optimize Price", use_container_width=True, type="primary"):
        with st.spinner("🔄 Optimizing price..."):
            try:
                # Prepare request payload
                payload = {
                    "product_id": product_id,
                    "competitor_price": competitor_price,
                    "dow": dow,
                    "is_weekend": is_weekend,
                    "week": week,
                    "month": month,
                    "sin_annual": sin_annual,
                    "cos_annual": cos_annual,
                    "lag_units_sold_1": lag_1,
                    "lag_units_sold_7": lag_7,
                    "lag_units_sold_14": lag_14,
                    "roll_mean_units_7": roll_mean_7,
                    "roll_mean_units_14": roll_mean_14,
                    "roll_mean_units_28": roll_mean_28,
                    "roll_std_units_7": roll_std_7,
                    "roll_std_units_14": roll_std_14,
                    "roll_std_units_28": roll_std_28,
                    "price_min": price_min,
                    "price_max": price_max,
                    "optimization_method": optimization_method,
                    "cost": cost,
                    "min_margin_pct": min_margin_pct,
                    "inventory_limit": inventory_limit if inventory_limit > 0 else None,
                }
                
                # Make API request
                response = requests.post(endpoint, json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Display results
                    st.success("✅ Optimization successful!")
                    
                    result_col1, result_col2, result_col3, result_col4 = st.columns(4)
                    
                    with result_col1:
                        st.metric(
                            "💰 Optimal Price",
                            f"${result['optimal_price']:.2f}",
                            f"vs Competitor: ${competitor_price:.2f}"
                        )
                    
                    with result_col2:
                        profit_per_unit = result['optimal_price'] - cost
                        margin = (profit_per_unit / result['optimal_price'] * 100) if result['optimal_price'] > 0 else 0
                        st.metric(
                            "📈 Profit Margin",
                            f"{margin:.1f}%",
                            f"${profit_per_unit:.2f} per unit"
                        )
                    
                    with result_col3:
                        st.metric(
                            "📊 Predicted Demand",
                            f"{result['predicted_demand']:.0f} units"
                        )
                    
                    with result_col4:
                        total_revenue = result['optimal_price'] * result['predicted_demand']
                        st.metric(
                            "💵 Est. Revenue",
                            f"${total_revenue:,.0f}"
                        )
                    
                    # Additional details
                    with st.expander("📋 Detailed Results"):
                        details_df = pd.DataFrame({
                            "Metric": [
                                "Optimal Price",
                                "Predicted Demand",
                                "Total Revenue",
                                "Total Cost",
                                "Total Profit",
                                "Price Change",
                                "Method"
                            ],
                            "Value": [
                                f"${result['optimal_price']:.2f}",
                                f"{result['predicted_demand']:.2f}",
                                f"${total_revenue:,.2f}",
                                f"${cost * result['predicted_demand']:,.2f}",
                                f"${(total_revenue - cost * result['predicted_demand']):,.2f}",
                                f"{((result['optimal_price'] - competitor_price) / competitor_price * 100):+.1f}%",
                                optimization_method
                            ]
                        })
                        st.dataframe(details_df, use_container_width=True)
                else:
                    st.error(f"❌ API Error: {response.status_code}")
                    st.error(response.text)
            
            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot connect to API. Make sure the server is running at: " + api_url)
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")


# ============= TAB 2: ADVANCED SETTINGS =============
with tab2:
    st.header("⚙️ Advanced Configuration")
    
    st.subheader("API Configuration")
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        **API Endpoint Details:**
        - Base URL: Enter in sidebar
        - Endpoint: `/v1/optimize-price`
        - Method: POST
        - Content-Type: application/json
        """)
    
    with col2:
        st.warning("""
        **Optimization Methods:**
        - **Bayesian**: Fast, Gaussian Process-based optimization
        - **Grid Search**: Exhaustive search over price range
        
        Choose based on your needs for speed vs accuracy.
        """)
    
    st.subheader("Request/Response Example")
    
    example_request = {
        "product_id": 42,
        "competitor_price": 89.99,
        "dow": 2,
        "is_weekend": 0,
        "week": 15,
        "month": 4,
        "sin_annual": 0.5,
        "cos_annual": 0.866,
        "lag_units_sold_1": 45.0,
        "lag_units_sold_7": 42.0,
        "lag_units_sold_14": 40.0,
        "roll_mean_units_7": 43.5,
        "roll_mean_units_14": 41.2,
        "roll_mean_units_28": 39.8,
        "roll_std_units_7": 5.2,
        "roll_std_units_14": 6.1,
        "roll_std_units_28": 7.3,
        "price_min": 70.0,
        "price_max": 110.0,
        "cost": 60.0,
        "min_margin_pct": 0.15,
        "inventory_limit": 100
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Example Request")
        st.json(example_request)
    
    with col2:
        st.subheader("Example Response")
        example_response = {
            "optimal_price": 95.50,
            "predicted_demand": 48.3,
            "confidence_interval": [45.2, 51.4],
            "optimization_metadata": {
                "method": "bayesian",
                "iterations": 25,
                "time_ms": 324
            }
        }
        st.json(example_response)


# ============= TAB 3: BATCH PRICING =============
with tab3:
    st.header("📈 Batch Pricing")
    
    st.info("Upload a CSV file with multiple products to optimize prices in bulk.")
    
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type="csv",
        help="CSV must have columns: product_id, competitor_price, etc."
    )
    
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.write("Preview of uploaded data:")
        st.dataframe(df.head())
        
        if st.button("🚀 Optimize All Products", type="primary"):
            progress_bar = st.progress(0)
            results = []
            
            for idx, row in df.iterrows():
                try:
                    # Prepare payload from row
                    payload = {
                        "product_id": int(row.get('product_id', 0)),
                        "competitor_price": float(row['competitor_price']),
                        "dow": int(row.get('dow', 2)),
                        "is_weekend": int(row.get('is_weekend', 0)),
                        "week": int(row.get('week', 15)),
                        "month": int(row.get('month', 4)),
                        "sin_annual": float(row.get('sin_annual', 0.5)),
                        "cos_annual": float(row.get('cos_annual', 0.866)),
                        "lag_units_sold_1": float(row.get('lag_units_sold_1', 45.0)),
                        "lag_units_sold_7": float(row.get('lag_units_sold_7', 42.0)),
                        "lag_units_sold_14": float(row.get('lag_units_sold_14', 40.0)),
                        "roll_mean_units_7": float(row.get('roll_mean_units_7', 43.5)),
                        "roll_mean_units_14": float(row.get('roll_mean_units_14', 41.2)),
                        "roll_mean_units_28": float(row.get('roll_mean_units_28', 39.8)),
                        "roll_std_units_7": float(row.get('roll_std_units_7', 5.2)),
                        "roll_std_units_14": float(row.get('roll_std_units_14', 6.1)),
                        "roll_std_units_28": float(row.get('roll_std_units_28', 7.3)),
                        "price_min": float(row.get('price_min', 70.0)),
                        "price_max": float(row.get('price_max', 110.0)),
                        "cost": float(row.get('cost', 60.0)),
                    }
                    
                    response = requests.post(endpoint, json=payload, timeout=30)
                    if response.status_code == 200:
                        result = response.json()
                        results.append({
                            "product_id": payload["product_id"],
                            "competitor_price": payload["competitor_price"],
                            "optimal_price": result["optimal_price"],
                            "predicted_demand": result["predicted_demand"],
                            "price_change_%": ((result["optimal_price"] - payload["competitor_price"]) / payload["competitor_price"] * 100),
                        })
                
                except Exception as e:
                    st.warning(f"Error processing row {idx}: {str(e)}")
                
                progress_bar.progress((idx + 1) / len(df))
            
            if results:
                results_df = pd.DataFrame(results)
                st.success(f"✅ Optimized {len(results)} products")
                st.dataframe(results_df, use_container_width=True)
                
                # Download results
                csv = results_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Results",
                    data=csv,
                    file_name="pricing_optimization_results.csv",
                    mime="text/csv"
                )


# ============= TAB 4: ABOUT =============
with tab4:
    st.header("📚 About Dynamic Pricing Engine")
    
    st.markdown("""
    ### What is Dynamic Pricing?
    
    Dynamic pricing is an intelligent pricing strategy that adjusts product prices based on real-time 
    market conditions, demand forecasts, and business constraints. This engine uses machine learning 
    to optimize prices for maximum profitability.
    
    ### Key Features
    
    - **🤖 ML-Based Demand Forecasting**: XGBoost models predict future demand
    - **💰 Profit Optimization**: Bayesian and grid search methods find optimal prices
    - **📊 Real-Time Data**: Considers competitor prices, seasonality, and historical trends
    - **🔒 Business Constraints**: Respects margins, inventory, and price ranges
    - **📈 Batch Processing**: Optimize multiple products simultaneously
    
    ### How It Works
    
    1. **Feature Engineering**: Calendar features, competitor analysis, and sales history
    2. **Demand Prediction**: ML model forecasts demand at different price points
    3. **Price Optimization**: Algorithm finds the price that maximizes revenue/profit
    4. **Business Rules**: Applies constraints (margins, inventory, price bounds)
    5. **Result**: Recommended optimal price for the product
    
    ### Architecture
    
    - **API Backend**: FastAPI with production-grade monitoring
    - **ML Models**: XGBoost for demand forecasting
    - **Optimization**: Bayesian optimization or grid search
    - **Frontend**: Streamlit UI for easy interaction
    - **Deployment**: Docker containerized for cloud platforms
    
    ### Use Cases
    
    ✅ E-commerce platforms  
    ✅ Subscription services  
    ✅ Ride-sharing apps  
    ✅ Hotels and accommodations  
    ✅ Airline ticket pricing  
    ✅ Product pricing in retail  
    
    ### Support
    
    For issues or questions, check the documentation or contact support.
    """)
    
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("📖 [Documentation](https://github.com)")
    with col2:
        st.info("🐛 [Report Issues](https://github.com)")
    with col3:
        st.info("⭐ [GitHub](https://github.com)")

# Footer
st.divider()
st.markdown("""
    <div align="center">
    <p style="color: #666; font-size: 12px;">
    Dynamic Pricing Engine v1.0 | Production Ready | Powered by ML & FastAPI
    </p>
    </div>
    """, unsafe_allow_html=True)
