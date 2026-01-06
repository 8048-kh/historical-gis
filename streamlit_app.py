import leafmap.foliumap as leafmap
import pandas as pd
import streamlit as st
import folium
import geopandas as gpd # 新增：用於過濾空間資料

st.set_page_config(layout="wide")

st.title("原鄉部落座標與資訊 📍")

# 定義欄位名稱
N_LAT_COL = 'NT_lat'
N_LON_COL = 'NT_lon'
O_LAT_COL = 'OT_lat'
O_LON_COL = 'OT_lon'
O_NAME_COL = 'o_tribe'
TRIBE_ID_COL = 'n_tribe' # 假設空間資料中對應部落名稱的欄位名

# 初始化地圖
m = leafmap.Map(center=[23.97565, 120.9738819], zoom=7)

# 增加底圖切換器 (讓使用者可以手動關閉地形圖)
# 日治番地地形圖圖層
m.add_tile_layer(
    url="http://gis.sinica.edu.tw/tileserver/file-exists.php?img=JM50K_1916-jpg-{z}-{x}-{y}",
    name="「1916-日治原住民地地形圖-1:50,000」",
    attribution="台灣百年歷史地圖 (中研院)",
    opacity=0.8
)

# 1. 載入 CSV 資料
tribes_url = "https://github.com/8048-kh/test02/raw/refs/heads/main/T_Result1.csv"
try:
    tribes_df = pd.read_csv(tribes_url)
    tribe_names = sorted(tribes_df['n_tribe'].dropna().unique().tolist())
except Exception as e:
    st.error(f"無法載入部落資料：{e}")
    st.stop()

# Streamlit 介面：選擇部落
selected_tribe = st.selectbox("選擇部落：", tribe_names, key="selectbox_tribe")
selected_data = tribes_df[tribes_df['n_tribe'] == selected_tribe].copy()

# ---------------------------------------------------------
# 2. 處理並過濾空間資料 (SHP 與 GeoJSON)
# ---------------------------------------------------------

# A. 處理部落 SHP (改用 geopandas 過濾)
shp_url = "https://github.com/8048-kh/test02/raw/refs/heads/main/tribe.shp"
try:
    # 讀取 SHP
    gdf_shp = gpd.read_file(shp_url)
    # 過濾：只保留名稱與選擇部落相同的多邊形 (請確認 'NAME' 是否為該 SHP 內的欄位名)
    # 如果欄位名稱不同，請修改下面的 'NAME'
    filtered_shp = gdf_shp[gdf_shp['tribe name'] == selected_tribe] 
    
    if not filtered_shp.empty:
        m.add_gdf(filtered_shp, layer_name=f"{selected_tribe} 區域")
except Exception as e:
    st.warning(f"無法過濾 SHP 圖層: {e}")

# B. 處理流向線 GeoJSON (過濾)
geojson_url = "https://github.com/8048-kh/test02/raw/refs/heads/main/flow_line_4326.geojson"
try:
    gdf_flow = gpd.read_file(geojson_url)
    # 過濾：假設 GeoJSON 內有欄位紀錄該線段屬於哪個部落 (例如 'Tribe')
    # 請將 'Tribe' 修改為您 GeoJSON 檔案中實際的屬性名稱
    filtered_flow = gdf_flow[gdf_flow['goal_tribe'] == selected_tribe]
    
    if not filtered_flow.empty:
        m.add_gdf(filtered_flow, layer_name="Flow lines (Filtered)")
except Exception as e:
    st.warning(f"無法過濾 GeoJSON 流向線: {e}")

# ---------------------------------------------------------
# 3. 標記標籤 (Marker 邏輯維持不變)
# ---------------------------------------------------------

n_lat, n_lon = None, None
if not selected_data.empty:
    n_lat = selected_data[N_LAT_COL].iloc[0]
    n_lon = selected_data[N_LON_COL].iloc[0]

    # 主要部落標記
    m.add_marker(
        location=(n_lat, n_lon),
        tooltip=selected_tribe,
        popup=f"{selected_tribe}<br>經度: {n_lon:.4f}<br>緯度: {n_lat:.4f}",
        icon=folium.Icon(color='blue', icon='star', prefix='fa')
    )
    m.set_center(n_lon, n_lat, zoom=15)

# 子部落標記與列表
o_tribe_data = selected_data.dropna(subset=[O_NAME_COL, O_LAT_COL, O_LON_COL])
o_tribe_names_list = []

if not o_tribe_data.empty:
    sub_icon_style = {'color': 'purple', 'icon': 'map-pin', 'prefix': 'fa'}
    for _, row in o_tribe_data.iterrows():
        o_lat, o_lon, o_name = row[O_LAT_COL], row[O_LON_COL], row[O_NAME_COL]
        is_main = (n_lat is not None and abs(o_lat - n_lat) < 0.0001 and abs(o_lon - n_lon) < 0.0001)
        
        if o_name and not is_main:
            m.add_marker(
                location=(o_lat, o_lon),
                tooltip=o_name,
                icon=folium.Icon(**sub_icon_style)
            )
            o_tribe_names_list.append(o_name)

    unique_o_tribe_names = sorted(list(set(o_tribe_names_list)))
    if unique_o_tribe_names:
        st.subheader(f"📌 {selected_tribe} 居民原居地：") 
        st.info("、".join(unique_o_tribe_names))
else:
    st.subheader(f"📌 {selected_tribe} 主要資訊 (無子部落紀錄)")
    st.dataframe(selected_data.head(1).T.fillna('-'))

# 最後顯示地圖前，增加一個 Layer Control (很重要，這樣才能開關地形圖)
folium.LayerControl().add_to(m)

# 顯示地圖
m.to_streamlit(height=700)
