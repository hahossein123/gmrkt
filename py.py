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
    imp_exp_df = pd.read_excel('imp and exp 1401.xlsx')
    routes_df = pd.read_excel('output.xlsx')

    # حذف فاصله اضافی از ستون‌ها و بررسی
    for df in [transit_df, imp_exp_df, routes_df]:
        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.strip()

    routes_df = routes_df.dropna(subset=['enter', 'exit'])

    # بررسی وجود ستون‌های «نوع مرز» و اطلاع‌رسانی به کاربر
    if 'نوع مرز ورودی' not in routes_df.columns or 'نوع مرز خروجی' not in routes_df.columns:
        st.error(
            "لطفاً فایل `output.xlsx` را به‌روزرسانی کنید و ستون‌های 'نوع مرز ورودی' و 'نوع مرز خروجی' را اضافه نمایید.")

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

    # انتخاب پروژه (Scenario)
    selected_project = None
    project_impact_dict = {}
    if not scenarios_df.empty:
        all_projects = scenarios_df['پروژه'].unique().tolist()
        selected_project = st.selectbox(
            "انتخاب پروژه (Scenario):",
            ['بدون پروژه/تاثیر'] + all_projects
        )

        if selected_project and selected_project != 'بدون پروژه/تاثیر':
            # تاثیر هر پروژه بر زوج کشورها
            for idx, row in scenarios_df.iterrows():
                project_impact_dict[(row['pair'], row['پروژه'])] = row['Value']

    # فیلتر زوج کشورها براساس پروژه انتخاب‌شده
    if selected_project and selected_project != 'بدون پروژه/تاثیر':
        filtered_pairs = scenarios_df[scenarios_df['پروژه'] == selected_project]['pair'].unique().tolist()
    else:
        filtered_pairs = routes_df['pair'].unique().tolist()

    # انتخاب یک یا چند زوج کشور
    selected_pairs = st.multiselect(
        "انتخاب زوج کشور:",
        filtered_pairs,
        help="زوج کشور موردنظر را انتخاب کنید"
    )

    if not selected_pairs:
        st.info("لطفاً حداقل یک زوج کشور انتخاب کنید.")
    else:
        # تعداد ستون‌های نمایش زوج‌ها
        n_cols = 3
        cols = st.columns(n_cols)
        split_pairs = [selected_pairs[i::n_cols] for i in range(n_cols)]  # پخش زوج‌ها در ستون‌ها

        for col, pairs_in_col in zip(cols, split_pairs):
            with col:
                for pair in pairs_in_col:

                    # استایل باکس
                    st.markdown(
                        "<div style='border:2.5px solid #222; border-radius:13px; "
                        "margin:16px 0; padding:16px 10px 10px 10px; "
                        "background:#fff; box-shadow:0 2px 10px #eee; direction:rtl;'>",
                        unsafe_allow_html=True
                    )
                    with st.container():
                        # نمایش اطلاعات زوج کشور
                        st.markdown(f"### <span style='color:#218380'>زوج کشور: <b>{pair}</b></span>", unsafe_allow_html=True)

                        # --- کشویی‌های فیلتر نوع مرز برای این زوج خاص ---
                        available_enter_types = routes_df[routes_df['pair'] == pair]['نوع مرز ورودی'].dropna().unique().tolist()
                        available_exit_types = routes_df[routes_df['pair'] == pair]['نوع مرز خروجی'].dropna().unique().tolist()

                        selected_enter_types = st.multiselect(
                            f"انتخاب نوع مرز ورودی برای زوج [{pair}]:",
                            options=available_enter_types,
                            default=available_enter_types
                        )
                        selected_exit_types = st.multiselect(
                            f"انتخاب نوع مرز خروجی برای زوج [{pair}]:",
                            options=available_exit_types,
                            default=available_exit_types
                        )

                        # --- کل بار ترانزیت این زوج ---
                        pair_volume = None
                        if 'pair' in transit_df.columns:
                            row = transit_df[transit_df['pair'] == pair]
                            if not row.empty:
                                pair_volume_raw = row.iloc[0, 1]

                                # بررسی اثر پروژه بر زوج کشور
                                impact_percent = 0
                                if selected_project and selected_project != 'بدون پروژه/تاثیر':
                                    impact_percent = project_impact_dict.get((pair, selected_project), 0)

                                pair_volume = pair_volume_raw * (1 + impact_percent / 100)

                                # پیام‌ها و نمایش اثر پروژه
                                if impact_percent != 0:
                                    st.info(f"اثر پروژه **{selected_project}** روی [{pair}]: {impact_percent:+.1f}%")
                                    st.info(f"حجم کل بار ترانزیت این زوج کشور (پس از اثر پروژه): **{pair_volume:.2f}** تن (مقدار اولیه: {pair_volume_raw:.2f})")
                                else:
                                    st.info(f"حجم کل بار ترانزیت این زوج کشور: **{pair_volume:.2f}** تن")
                            else:
                                st.warning("برای این زوج کشور، داده‌ای موجود نیست.")
                        else:
                            st.warning("ستون pair در جدول یافت نشد!")

                        # تخصیص درصدی از کل بار
                        st.subheader("تخصیص درصدی از کل حجم این زوج")
                        allocation_percent = st.number_input(
                            f"چه درصدی از کل بار [{pair}] را می‌خواهید تقسیم کنید؟",
                            min_value=1.0, max_value=100.0, value=100.0, step=1.0, key=f"alloc_{pair}"
                        )
                        allocated_volume = pair_volume * allocation_percent / 100 if pair_volume else 0
                        st.info(
                            f"حجم قابل تخصیص به مسیرها: **{allocated_volume:.2f} تن** ({allocation_percent}٪ از {pair_volume})"
                            if pair_volume else "بار این زوج صفر است."
                        )

                        # فیلتر مسیرها براساس زوج کشور و نوع مرز ورودی/خروجی
                        st.subheader("تقسیم درصد تخصیص بین مسیرهای این زوج")
                        filtered_routes = routes_df[
                            (routes_df['pair'] == pair) &
                            (routes_df['نوع مرز ورودی'].isin(selected_enter_types)) &
                            (routes_df['نوع مرز خروجی'].isin(selected_exit_types))
                        ].copy()

                        if filtered_routes.empty:
                            st.warning("هیچ مسیری با فیلترهای انتخاب‌شده یافت نشد.")
                        else:
                            st.write(f"📋 تعداد مسیرهای یافت‌شده: {len(filtered_routes)}")
                            st.dataframe(filtered_routes[['pair', 'enter', 'نوع مرز ورودی', 'exit', 'نوع مرز خروجی']])

                        # تنظیم درصد تخصیصی برای مسیرها
                        default_percent = round(100 / len(filtered_routes), 2) if not filtered_routes.empty else 0

                        filtered_routes['درصد تخصیصی'] = [
                            st.number_input(
                                f"درصد تخصیص برای مسیر [{row['enter']} ← {row['exit']}]:",
                                min_value=0.0, max_value=100.0,
                                value=default_percent,
                                step=1.0,
                                key=f"alloc_{pair}_{i}"
                            ) for i, row in filtered_routes.iterrows()
                        ]

                        # محاسبه حجم براساس درصدها
                        sum_percent = sum(filtered_routes['درصد تخصیصی'])
                        if sum_percent > 100.0:
                            st.error("⚠️ مجموع درصدهای وارد‌شده نباید بیش از ۱۰۰ باشد!")
                        elif sum_percent < 1.0:
                            st.info("جمع درصد خیلی کم است.")
                        elif sum_percent != 100.0:
                            st.info("جمع درصد بهتر است دقیقاً ۱۰۰ باشد.")

                        # حجم عبوری تخصیص‌یافته به مسیرها
                        filtered_routes['حجم بار عبوری از این مسیر (تن)'] = [
                            allocated_volume * p / 100 for p in filtered_routes['درصد تخصیصی']
                        ]

                        # دکمه دانلود فایل مسیرهای فیلترشده
                        if not filtered_routes.empty:
                            st.download_button(
                                label="📥 دانلود داده‌های فیلتر‌شده برای این زوج",
                                data=filtered_routes.to_csv(index=False),
                                file_name=f"filtered_routes_{pair}.csv",
                                mime="text/csv"
                            )

                        # جمع‌بندی بار گمرکات
                        for _, row in filtered_routes.iterrows():
                            all_customs_results.append({
                                'گمرک': row['enter'],
                                'بار ترانزیتی تخصیص‌یافته': row['حجم بار عبوری از این مسیر (تن)'],
                                'pair': pair
                            })
                            all_customs_results.append({
                                'گمرک': row['exit'],
                                'بار ترانزیتی تخصیص‌یافته': row['حجم بار عبوری از این مسیر (تن)'],
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
    map_df['radius'] = np.sqrt(map_df['جمع کل (ترانزیت + تجارت ایران)']) * 5 + 50

    map_df['بار ترانزیتی تخصیص‌یافته'] = map_df['بار ترانزیتی تخصیص‌یافته'].apply(lambda x: f"{int(x):,}")
    map_df['تجارت ایران'] = map_df['تجارت ایران'].apply(lambda x: f"{int(x):,}")
    map_df['جمع کل (ترانزیت + تجارت ایران)'] = map_df['جمع کل (ترانزیت + تجارت ایران)'].apply(lambda x: f"{int(x):,}")
    map_df['ظرفیت'] = map_df['ظرفیت'].apply(lambda x: f"{int(x):,}")  # اگر ستون ظرفیت وجود دارد.

    # اطمینان از عدد بودن ستون‌ها (رفع فرمت جداکننده هزارگان)
    map_df['جمع کل (ترانزیت + تجارت ایران)_num'] = map_df['جمع کل (ترانزیت + تجارت ایران)'].str.replace(',', '').astype(
        float)
    map_df['ظرفیت_num'] = map_df['ظرفیت'].str.replace(',', '').astype(float)

    # اضافه کردن ستون وضعیت ظرفیت
    map_df['over_capacity'] = map_df['جمع کل (ترانزیت + تجارت ایران)_num'] > map_df['ظرفیت_num']

    # رنگ داخل دایره
    map_df['fill_color'] = map_df['over_capacity'].apply(
        lambda x: [230, 50, 50, 170] if x else [60, 210, 60, 180])
    # رنگ دور دایره
    map_df['border_color'] = map_df['over_capacity'].apply(
        lambda x: [200, 20, 20, 220] if x else [0, 150, 0, 220])

    # متن ارور برای Tooltip
    map_df['error_text'] = map_df['over_capacity'].apply(
        lambda x: "<br><span style='color:#D00000; font-weight:bold;'>⚠️ ظرفیت پایانه کافی نیست!</span>" if x else ""
    )

    # مرکز نقشه (میانگین مختصات)
    avg_lat = map_df['lat'].astype(float).mean()
    avg_long = map_df['long'].astype(float).mean()

    # لایه دایره‌ای
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position='[long, lat]',
        get_fill_color='fill_color',
        get_radius='radius',
        pickable=True,
        auto_highlight=True,
        get_line_color='border_color',
        line_width_min_pixels=3  # ضخامت دور دایره
    )

    # قالب Tooltip
    tooltip_html = (
        "<b>{گمرک}</b>"
        "<br>بار ترانزیت تخصیص‌یافته: <b>{بار ترانزیتی تخصیص‌یافته}</b> تن"
        "<br>تجارت ایران: <b>{تجارت ایران}</b> تن"
        "<br><span style='color:#2B50AA'>جمع کل: <b>{جمع کل (ترانزیت + تجارت ایران)}</b> تن</span>"
        "<br><span style='color:#FF8C00'>ظرفیت پایانه: <b>{ظرفیت}</b> تن</span>"
        "{error_text}"  # اضافه کردن متن ارور
    )

    # نمایش نقشه
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
            "html": tooltip_html,  # استفاده از قالب Tooltip بالا
            "style": {"color": "white"}  # تنظیم رنگ Tooltip
        }
    ))
