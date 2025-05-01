import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk

st.set_page_config(page_title="تحلیل اثر ترافیک ترانزیتی بر گمرکات ایران", layout="wide")

st.markdown("""
    <style>
    /* جهت دهی کلی راست به چپ */
    .main, .block-container, .stApp {
        direction: rtl !important;
        text-align: right !important;
    }
    /* تمام کامپوننت‌های درون جدول و دیتا فریم هم راست‌چین شوند */
    .css-1d391kg td, .css-1d391kg th, .stDataFrame td, .stDataFrame th {
        direction: rtl !important;
        text-align: right !important;
        unicode-bidi: plaintext !important;
    }
    /* هدرها و متن‌های معمولی هم راست‌چین باشند */
    .stMarkdown, .stText, .stHeader, .stSubheader, .stExpander, .element-container {
        direction: rtl !important;
        text-align: right !important;
        unicode-bidi: plaintext !important;
    }
    </style>
""", unsafe_allow_html=True)




# --- بارگذاری داده‌ها ---
@st.cache_data
def load_data():
    transit_df = pd.read_excel('transitfinal.xlsx')
    imp_exp_df = pd.read_csv('imp and exp 1401.csv')
    routes_df = pd.read_excel('output.xlsx')
    for df in [transit_df, imp_exp_df, routes_df]:
        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.strip()
    routes_df = routes_df.dropna(subset=['enter', 'exit'])
    return transit_df, imp_exp_df, routes_df

# --- بارگذاری داده‌های مختصات + ظرفیت ---
@st.cache_data
def load_location():
    loc_df = pd.read_excel('gmrk-lat-long-cap.xlsx')
    loc_df.columns = [c.strip() for c in loc_df.columns]
    return loc_df


loc_df = load_location()

transit_df, imp_exp_df, routes_df = load_data()
loc_df = load_location()

st.title("تحلیل اثر ترافیک ترانزیتی بر گمرکات ایران")

# --- بارگذاری داده‌های پروژه‌ها (scenarios) ---
@st.cache_data
def load_scenarios():
    try:
        scenarios_df = pd.read_excel('scenarios.xlsx')
        scenarios_df.columns = [c.strip() for c in scenarios_df.columns]
        return scenarios_df
    except Exception as e:
        st.warning("فایل scenarios.xlsx بارگذاری نشد.")
        return pd.DataFrame()

scenarios_df = load_scenarios()


# ---- متغیر اولیه ----
all_customs_results = []
selected_pairs = []

# -----------------------
# --- تنظیمات ترانزیت (در EXPANDER) ---
# -----------------------
with st.expander("تنظیمات ترانزیت ⚙️", expanded=False):


    # انتخاب پروژه (scenario)
    selected_project = None
    project_impact_dict = {}
    if not scenarios_df.empty:
        all_projects = scenarios_df['پروژه'].unique().tolist()
        selected_project = st.selectbox("انتخاب پروژه (Scenario):", ['بدون پروژه/تاثیر'] + all_projects)
        if selected_project and selected_project != 'بدون پروژه/تاثیر':
            # تاثیر هر پروژه بر هر زوج کشور را سریع قابل دسترس کنیم
            for idx, row in scenarios_df.iterrows():
                project_impact_dict[(row['pair'], row['پروژه'])] = row['Value']

    all_pairs = routes_df['pair'].unique().tolist()
    selected_pairs = st.multiselect("انتخاب یک یا چند زوج کشور:", all_pairs)

    if not selected_pairs:
        st.info("لطفاً حداقل یک زوج کشور انتخاب کنید.")
    else:
        n_cols = 3
        cols = st.columns(n_cols)
        split_pairs = [selected_pairs[i::n_cols] for i in range(n_cols)]  # پخش زوج‌ها بین ستون‌ها

        for col, pairs_in_col in zip(cols, split_pairs):
            with col:
                for pair in pairs_in_col:

                    # شروع باکس (به کمک st.markdown قبل و بعد container)
                    st.markdown(
                        "<div style='border:2.5px solid #222; border-radius:13px; "
                        "margin:16px 0; padding:16px 10px 10px 10px; "
                        "background:#fff; box-shadow:0 2px 10px #eee; direction:rtl;'>",
                        unsafe_allow_html=True
                    )
                    with st.container():
                        # همه اینها داخل باکس رندر می‌شوند:

                        st.markdown(f"### <span style='color:#218380'>زوج کشور: <b>{pair}</b></span>", unsafe_allow_html=True)

                        # --- کل بار ترانزیت این زوج ---
                        pair_volume = None
                        if 'pair' in transit_df.columns:
                            row = transit_df[transit_df['pair'] == pair]
                            if not row.empty:
                                pair_volume_raw = row.iloc[0, 1]
                                # تاثیر پروژه اگر انتخاب شده (مثبت یا منفی)
                                impact_percent = 0
                                if selected_project and selected_project != 'بدون پروژه/تاثیر':
                                    impact_percent = project_impact_dict.get((pair, selected_project), 0)
                                pair_volume = pair_volume_raw * (1 + impact_percent / 100)
                                # پیام درصد اثر را نمایش بده
                                if impact_percent != 0:
                                    st.info(f"اثر پروژه **{selected_project}** روی [{pair}]: {impact_percent:+.1f}%")
                                    st.info(
                                        f"حجم کل بار ترانزیت این زوج کشور (پس از اثر پروژه): **{pair_volume:.2f}** تن (مقدار اولیه: {pair_volume_raw:.2f})")
                                else:
                                    st.info(f"حجم کل بار ترانزیت این زوج کشور: **{pair_volume:.2f}** تن")
                            else:
                                st.warning("برای این زوج کشور، در جدول حجم بار کلی داده‌ای وجود ندارد.")
                        else:
                            st.warning("ستون pair در جدول transitfinal.xlsx یافت نشد!")

                        st.subheader("تخصیص درصدی از کل حجم این زوج")
                        allocation_percent = st.number_input(
                            f"چه درصدی از کل بار [{pair}] را می‌خواهید تقسیم کنید؟",
                            min_value=1.0, max_value=100.0, value=100.0, step=1.0, key=f"alloc_{pair}"
                        )
                        allocated_volume = pair_volume * allocation_percent / 100 if pair_volume else 0
                        st.info(f"حجم قابل تخصیص به مسیرها: **{allocated_volume:.2f} تن** ({allocation_percent}٪ از {pair_volume})" if pair_volume else "بار این زوج صفر است.")

                        st.subheader("تقسیم درصد تخصیص بین مسیرهای این زوج")
                        filtered_routes = routes_df[routes_df['pair'] == pair].copy()
                        filtered_routes['مسیر'] = filtered_routes['enter'] + " ← " + filtered_routes['exit']
                        default_percent = round(100/len(filtered_routes), 2) if not filtered_routes.empty else 0
                        if 'percent' not in filtered_routes.columns:
                            filtered_routes['percent'] = default_percent

                        percentages = []
                        for i, rowr in filtered_routes.iterrows():
                            pct = st.number_input(
                                f"درصد تخصیصی برای مسیر [{rowr['مسیر']}] ({pair}):",
                                min_value=0.0, max_value=100.0,
                                value=float(rowr['percent']) if not pd.isna(rowr['percent']) else default_percent,
                                key=f"percent_{pair}_{i}",
                                step=0.1
                            )
                            percentages.append(pct)

                        filtered_routes['درصد تخصیصی'] = [round(p, 2) for p in percentages]
                        sum_percent = round(sum(percentages), 2)
                        st.markdown("---")
                        st.warning(f"**مجموع درصدهای وارد شده برای این زوج:** {sum_percent}٪")
                        if sum_percent > 100.0:
                            st.error('⚠️ مجموع درصدها نباید بیش از ۱۰۰ باشد!')
                        elif sum_percent < 1.0:
                            st.info('جمع درصد خیلی کم است.')
                        elif sum_percent != 100.0:
                            st.info('مجموع درصدها بهتر است دقیقاً ۱۰۰ باشد.')

                        if allocated_volume:
                            filtered_routes['حجم بار عبوری از این مسیر (تن)'] = [
                                round(allocated_volume * p / 100, 2) for p in filtered_routes['درصد تخصیصی']
                            ]
                        else:
                            filtered_routes['حجم بار عبوری از این مسیر (تن)'] = 0

                        show_cols = ['مسیر', 'درصد تخصیصی', 'حجم بار عبوری از این مسیر (تن)']
                        st.dataframe(filtered_routes[show_cols])

                        # جمع بار هر گمرک وارد/خروجی
                        for i, rowr in filtered_routes.iterrows():
                            all_customs_results.append({
                                'گمرک': rowr['enter'],
                                'بار ترانزیتی تخصیص‌یافته': rowr['حجم بار عبوری از این مسیر (تن)'],
                                'pair': pair
                            })
                            all_customs_results.append({
                                'گمرک': rowr['exit'],
                                'بار ترانزیتی تخصیص‌یافته': rowr['حجم بار عبوری از این مسیر (تن)'],
                                'pair': pair
                            })

                    st.markdown("</div>", unsafe_allow_html=True)


# ======================
# جدول نهایی بار عبوری کل از هر گمرک (ترانزیت همه زوج‌ها + تجارت ایران)
# ======================
if all_customs_results:
    with st.expander("جدول نهایی: بار عبوری + تجارت ایران هر گمرک", expanded=False):
        customs_concs = pd.DataFrame(all_customs_results)
        customs_summary = (
            customs_concs.groupby('گمرک')['بار ترانزیتی تخصیص‌یافته']
            .sum().reset_index()
        )

        # الحاق به داده تجارت ایران
        col_enter = 'نام گمرک جدید'
        col_value = 'Sum of ton'
        imported = imp_exp_df.rename(columns={col_enter:'گمرک', col_value:'تجارت ایران'})
        imported['تجارت ایران'] = pd.to_numeric(imported['تجارت ایران'], errors='coerce').fillna(0)

        final = pd.merge(customs_summary, imported[['گمرک','تجارت ایران']], how='outer', on='گمرک').fillna(0)
        final['جمع کل (ترانزیت + تجارت ایران)'] = final['بار ترانزیتی تخصیص‌یافته'] + final['تجارت ایران']
        final = final[['گمرک', 'بار ترانزیتی تخصیص‌یافته', 'تجارت ایران', 'جمع کل (ترانزیت + تجارت ایران)']].sort_values('جمع کل (ترانزیت + تجارت ایران)', ascending=False)
        final = final.reset_index(drop=True)

        st.dataframe(final)
else:
    st.info("برای نمایش جدول نهایی، ابتدا تنظیمات ترانزیت را انتخاب و اعمال کنید.")


# ================ نقشه ===================
st.subheader("نمای گرافیکی روی نقشه گمرکات")

if all_customs_results:
    map_df = pd.merge(final, loc_df, left_on='گمرک', right_on='نام گمرک جدید', how='inner')

else:
    map_df = pd.DataFrame()

if map_df.empty:
    st.warning("داده‌ای برای نمایش روی نقشه وجود ندارد. لطفاً تنظیمات ترانزیت را انتخاب و ذخیره کنید.")
else:
    # محاسبه رادیوس نرمال‌شده بر اساس مقدار جمع کل
    map_df['radius'] = np.sqrt(map_df['جمع کل (ترانزیت + تجارت ایران)']) * 10 + 100

    # مرکز نقشه (میانگین مختصات)
    avg_lat = map_df['lat'].astype(float).mean()
    avg_long = map_df['long'].astype(float).mean()

    # لایه دایره‌ای
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position='[long, lat]',
        get_fill_color='[30, 100, 210, 140]',
        get_radius='radius',
        pickable=True,
        auto_highlight=True
    )

    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/light-v9',
        initial_view_state=pdk.ViewState(
            latitude=avg_lat,
            longitude=avg_long,
            zoom=5,
            pitch=0,
        ),
        layers=[layer],
        tooltip={
            "html": (
                "<b>{گمرک}</b>"
                "<br>بار ترانزیت تخصیص‌یافته: <b>{بار ترانزیتی تخصیص‌یافته}</b> تن"
                "<br>تجارت ایران: <b>{تجارت ایران}</b> تن"
                "<br><span style='color:#2B50AA'>جمع کل: <b>{جمع کل (ترانزیت + تجارت ایران)}</b> تن</span>"
                "<br><span style='color:#FF8C00'>ظرفیت پایانه: <b>{ظرفیت}</b> تن</span>"
            ),
            "style": {"color": "white"}
        }

    ))
