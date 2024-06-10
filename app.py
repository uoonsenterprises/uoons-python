from flask import Flask, request, jsonify
import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt

app = Flask(__name__)
user = 'admin'
password = 'Uoons#123'
host = 'uoons-db.cl2u84igizk9.ap-south-1.rds.amazonaws.com'
port = '3306'
database = 'newdb'
connection_string = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
engine = create_engine(connection_string)
tables = ['order_history', 'user', 'recently_view', 'seller', 'user_address', 'user_order_address', 'products']
dataframes = {}
for table in tables:
    query = f"SELECT * FROM {table}"
    try:
        df = pd.read_sql_query(query, engine)
        dataframes[table] = df
        # print(f"Data fetched successfully for table: {table}")
    except Exception as e:
        print(f"Error fetching data for table {table}: {e}")

df_order_history = dataframes['order_history']
df_user = dataframes['user']
df_recently_viewed = dataframes['recently_view']
df_seller = dataframes['seller']
df_user_address = dataframes['user_address']
df_user_order_address = dataframes['user_order_address']
df_products = dataframes['products']

def get_seller_info(seller_id, columns=None):
    seller_data = df_order_history[df_order_history['seller_id'] == seller_id]
    if columns:
        seller_data = seller_data[columns]
    return seller_data

def filter_seller_data(seller_id, df):
    return df[df['seller_id'] == seller_id]

@app.route('/seller_dashboard', methods=['POST'])
def graph_data():
    data = request.json
    user_input = data.get('url')
    seller_id = int(user_input)
    
    seller_info = get_seller_info(seller_id, columns=['pid', 'user_id'])
    seller_data = filter_seller_data(seller_id, df_order_history)
    
    response_data = {}

    # Plotting per product sales
    if not seller_info.empty:
        g_x_1 = list(seller_info['pid'])
        g_y_1 = list(seller_info['user_id'])
        response_data["per_product_sales"] = {"x": g_x_1, "y": g_y_1}
    
    # Group data by product ID and payment method, and count the number of occurrences
    if not seller_data.empty:
        product_payment_counts = seller_data.groupby(['pid', 'payment_method']).size().unstack(fill_value=0)
        product_ids = product_payment_counts.index
        index = list(range(len(product_ids)))
        
        width = 0.35
        fig, ax = plt.subplots()
        cod_bars = ax.bar([i - width/2 for i in index], product_payment_counts.get('COD', 0), width, label='COD')
        
        online_bars = ax.bar([i + width/2 for i in index], product_payment_counts.get('ONLINE', 0), width, label='Online')
        payment_method_counts = []

        for pid in product_ids:
            cod_count = product_payment_counts.at[pid, 'COD'] if 'COD' in product_payment_counts.columns else 0
            online_count = product_payment_counts.at[pid, 'ONLINE'] if 'ONLINE' in product_payment_counts.columns else 0
            payment_method_counts.append({
                "p_id": pid,
                "COD": cod_count,
                "ONLINE": online_count
            })
        response_data["payment_method_distribution"] = payment_method_counts
    # Pie chart for unique users per product
    sales_data = seller_data.groupby('pid')['user_id'].nunique()
    pie_graph_coords = [{"label": label, "value": value} for label, value in zip(sales_data.index, sales_data)]
    response_data["unique_users_pie_chart"] = pie_graph_coords
    
    # Most viewed products
    p_ids = df_products['pid'].unique()
    filtered_recently_view = df_recently_viewed[df_recently_viewed['p_id'].isin(p_ids)]
    p_id_counts = filtered_recently_view['p_id'].value_counts()
    
    if not p_id_counts.empty:
        top_10_p_id_counts = p_id_counts.head(10)
        
        g_x_2 = list(top_10_p_id_counts.index)
        g_y_2 = list(top_10_p_id_counts.values)
        response_data["most_viewed_products"] = {"x": g_x_2, "y": g_y_2}
    
    # Most sold products
    product_sales = seller_data.groupby('pid')['amount'].sum()
    most_sold_product_coords = [{"product_id": pid, "sales": amount} for pid, amount in product_sales.items()]
    response_data["most_sold_product"] = most_sold_product_coords

    return jsonify(f"{response_data}")

if __name__ == '__main__':
    app.run(debug=True)
